# ⚠️ IMPORTANT: Le monkey patching est fait UNIQUEMENT dans wsgi.py
# Ne JAMAIS patcher ici pour éviter les conflits de locks avec gevent/eventlet
# Sur Render, wsgi.py est le point d'entrée et fait le patching avant tout import

# Charger les variables d'environnement depuis .env (développement local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, send_file, send_from_directory, jsonify, make_response, has_request_context
import sqlite3
import re
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date, datetime, timedelta
import secrets
import os
import random
import string
import base64
import uuid
import json
import requests
import time

# ─── COUCHE DE COMPATIBILITÉ DB (SQLite local / PostgreSQL Render) ──────────
# Détecte automatiquement l'env Render via DATABASE_URL
_PG_URL = os.environ.get('DATABASE_URL', '')
if _PG_URL.startswith('postgres://'):
    _PG_URL = _PG_URL.replace('postgres://', 'postgresql://', 1)
_USE_PG = bool(_PG_URL)

if _USE_PG:
    try:
        import psycopg2
        # psycopg2.pool N'EST PLUS UTILISÉ (incompatible avec gevent/eventlet)
    except ImportError:
        _USE_PG = False

# ⚠️ POOL DÉSACTIVÉ : Les pools psycopg2 ne sont pas compatibles avec gevent/eventlet
# Les connexions directes sont plus stables, même si légèrement plus lentes
# (alternative: utiliser psycogreen avec gevent, mais ajoute une dépendance)

_RE_INSERT = re.compile(r'^\s*INSERT\s+', re.IGNORECASE)
_RE_ALTER_ADD = re.compile(
    r'(ALTER\s+TABLE\s+\S+\s+ADD\s+COLUMN\s+)(?!IF\s+NOT\s+EXISTS\s)',
    re.IGNORECASE
)
# ─── Traduction SQLite → PostgreSQL : fonctions de date ───────────────────────
# strftime('%w', DATE(col)) → EXTRACT(DOW ...)
_RE_STRFTIME_W = re.compile(
    r"CAST\s*\(\s*strftime\s*\(\s*'%w'\s*,\s*DATE\s*\(([^,)]+?)(?:,\s*'localtime')?\s*\)\s*\)\s+AS\s+INTEGER\s*\)",
    re.IGNORECASE
)
# datetime(date('now','localtime','+N day')) → (CURRENT_DATE + INTERVAL 'N day')::timestamp
_RE_DATETIME_DATE_NOW_OFFSET = re.compile(
    r"datetime\s*\(\s*date\s*\(\s*'now'\s*,\s*'localtime'\s*,\s*'([^']+)'\s*\)\s*\)",
    re.IGNORECASE
)
# datetime(date('now','localtime')) → CURRENT_TIMESTAMP
_RE_DATETIME_DATE_NOW_LOCAL = re.compile(
    r"datetime\s*\(\s*date\s*\(\s*'now'\s*,\s*'localtime'\s*\)\s*\)",
    re.IGNORECASE
)
# datetime(col) → col::timestamp
_RE_DATETIME_COL = re.compile(
    r"datetime\s*\(\s*([^()]+?)\s*\)",
    re.IGNORECASE
)
# date('now','localtime','+N day') → CURRENT_DATE + INTERVAL 'N day'
_RE_DATE_NOW_OFFSET = re.compile(
    r"date\s*\(\s*'now'\s*,\s*'localtime'\s*,\s*'([^']+)'\s*\)",
    re.IGNORECASE
)
# date('now','localtime') → CURRENT_DATE
_RE_DATE_NOW_LOCAL = re.compile(
    r"date\s*\(\s*'now'\s*,\s*'localtime'\s*\)",
    re.IGNORECASE
)
# date('now') → CURRENT_DATE
_RE_DATE_NOW = re.compile(
    r"date\s*\(\s*'now'\s*\)",
    re.IGNORECASE
)
# DATE(col) → col::date  (doit être APRÈS les patterns ci-dessus)
_RE_DATE_LOCALTIME = re.compile(r"DATE\(([^,)]+),\s*'localtime'\)", re.IGNORECASE)
# date(col) isolé (sans 'now') → col::date
_RE_DATE_COL = re.compile(
    r"\bdate\s*\(\s*([^'(),]+?)\s*\)",
    re.IGNORECASE
)


class _CompatCursor:
    """
    Curseur compatible sqlite3/psycopg2 :
    - ? → %s pour PostgreSQL
    - INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
    - PRAGMA ignoré silencieusement
    - lastrowid via RETURNING id
    - ADD COLUMN → ADD COLUMN IF NOT EXISTS (migration sans erreur)
    """
    def __init__(self, cur, is_pg=False):
        self._cur = cur
        self._is_pg = is_pg
        self.lastrowid = None
        self.rowcount = 0
        self._pragma_mode = False

    def _adapt(self, sql):
        if not self._is_pg:
            return sql
        sql = sql.replace('?', '%s')
        sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        sql = sql.replace('DATETIME DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        sql = sql.replace(' DATETIME ', ' TIMESTAMP ')
        sql = _RE_ALTER_ADD.sub(r'\1IF NOT EXISTS ', sql)
        # ─── SQLite → PostgreSQL : Traduction des fonctions de date ───
        # ORDRE CRITIQUE : les patterns les plus spécifiques d'abord
        # 1) strftime('%w', ...) → EXTRACT DOW
        sql = _RE_STRFTIME_W.sub(r'EXTRACT(DOW FROM \1::date)::integer', sql)
        # 2) datetime(date('now','localtime','+N day')) → (CURRENT_DATE + INTERVAL 'N day')::timestamp
        sql = _RE_DATETIME_DATE_NOW_OFFSET.sub(r"(CURRENT_DATE + INTERVAL '\1')::timestamp", sql)
        # 3) datetime(date('now','localtime')) → CURRENT_TIMESTAMP
        sql = _RE_DATETIME_DATE_NOW_LOCAL.sub('CURRENT_TIMESTAMP', sql)
        # 4) datetime(col) → col::timestamp
        sql = _RE_DATETIME_COL.sub(r'\1::timestamp', sql)
        # 5) date('now','localtime','+N day') → CURRENT_DATE + INTERVAL 'N day'
        sql = _RE_DATE_NOW_OFFSET.sub(r"CURRENT_DATE + INTERVAL '\1'", sql)
        # 6) date('now','localtime') → CURRENT_DATE
        sql = _RE_DATE_NOW_LOCAL.sub('CURRENT_DATE', sql)
        # 7) date('now') → CURRENT_DATE
        sql = _RE_DATE_NOW.sub('CURRENT_DATE', sql)
        # 8) DATE(col) → col::date
        sql = _RE_DATE_LOCALTIME.sub(r'\1::date', sql)
        # 9) date(col) isolé → col::date
        sql = _RE_DATE_COL.sub(r'\1::date', sql)
        return sql

    def execute(self, sql, params=()):
        self._pragma_mode = False
        if self._is_pg and sql.strip().upper().startswith('PRAGMA'):
            self._pragma_mode = True
            self.rowcount = 0
            return
        sql = self._adapt(sql)
        if self._is_pg and _RE_INSERT.match(sql) and 'RETURNING' not in sql.upper():
            sql = sql + ' RETURNING id'
            try:
                self._cur.execute(sql, params if params else ())
            except Exception:
                try:
                    self._cur.connection.rollback()
                except Exception:
                    pass
                raise
            row = self._cur.fetchone()
            self.lastrowid = row[0] if row else None
            self.rowcount = self._cur.rowcount
            return
        try:
            self._cur.execute(sql, params if params else ())
        except Exception:
            if self._is_pg:
                # PostgreSQL: rollback automatique pour débloquer la transaction
                try:
                    self._cur.connection.rollback()
                except Exception:
                    pass
            raise
        if not self._is_pg:
            self.lastrowid = getattr(self._cur, 'lastrowid', None)
        self.rowcount = self._cur.rowcount

    def executemany(self, sql, params_list):
        sql = self._adapt(sql)
        self._cur.executemany(sql, params_list)
        self.rowcount = self._cur.rowcount

    def fetchone(self):
        if self._pragma_mode:
            return None
        return self._cur.fetchone()

    def fetchall(self):
        if self._pragma_mode:
            return []
        return self._cur.fetchall()

    @property
    def description(self):
        return self._cur.description

    def __iter__(self):
        return iter(self._cur)


class _CompatConn:
    """Connexion compatible sqlite3/psycopg2."""
    def __init__(self, conn, is_pg=False, pool=None):
        self._conn = conn
        self._is_pg = is_pg
        # pool ignoré - conservé pour compatibilité avec ancien code

    def cursor(self):
        return _CompatCursor(self._conn.cursor(), self._is_pg)

    def execute(self, sql, params=()):
        """conn.execute() direct style sqlite3."""
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try:
                self._conn.rollback()
            except Exception:
                pass
        else:
            try:
                self._conn.commit()
            except Exception:
                pass
        self.close()
        return False


# Alias erreurs DB (sqlite3 vs psycopg2)
_DBIntegrityError = (sqlite3.IntegrityError,)
if _USE_PG:
    _DBIntegrityError = _DBIntegrityError + (psycopg2.IntegrityError,)
# ────────────────────────────────────────────────────────────────────────────

# 🚀 PERFORMANCE: Prints de debug désactivés par défaut
# Pour réactiver: lancer avec CLEANBEAT_DEBUG=1 python3 app.py
_DEBUG = os.environ.get('CLEANBEAT_DEBUG', '') == '1'
def _dbg(*args, **kwargs):
    """Print de debug silencieux sauf si CLEANBEAT_DEBUG=1"""
    if _DEBUG:
        print(*args, **kwargs)

def safe_socketio_emit(event, data, **kwargs):
    """
    🛡️ Wrapper sécurisé pour socketio.emit() qui gère les sessions invalides.
    
    Sur Render, quand le service s'endort ou redémarre, les sessions SocketIO deviennent
    invalides et socketio.emit() peut lever des exceptions 'Invalid session' ou 
    'Session is disconnected', causant des erreurs HTTP 500.
    
    Cette fonction entoure l'appel avec try/except pour éviter les crashs.
    
    Args:
        event: Nom de l'événement WebSocket
        data: Données à envoyer
        **kwargs: Arguments passés à socketio.emit (namespace, room, broadcast, etc.)
    
    Returns:
        True si l'émission a réussi, False sinon
    """
    if not SOCKETIO_AVAILABLE or not socketio:
        _dbg(f"⚠️ WebSocket non disponible, impossible d'émettre '{event}'")
        return False
    
    try:
        socketio.emit(event, data, **kwargs)
        return True
    except Exception as e:
        # Erreurs typiques sur Render : 'Invalid session', 'Session is disconnected'
        _dbg(f"⚠️ Erreur WebSocket lors de l'émission '{event}': {e}")
        return False

# Pour l'envoi de SMS (Twilio)

import base64
import uuid
import json
import requests
# Pour l'envoi de SMS (Twilio)

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Twilio non installé. Installation: pip install twilio")

# ...existing code...
from name_house import bp as name_house_bp

# Route pour supprimer une tâche personnalisée (à placer après la création de l'objet app)
def register_delete_custom_task_route(app):
    @app.route('/delete_custom_task/<int:task_id>/<cat>', methods=['POST'])
    def delete_custom_task(task_id, cat):
        if 'user' not in session:
            flash("Connecte-toi pour supprimer une mission.", "warning")
            return redirect(url_for('login'))

        conn = get_db_connection()
        c = conn.cursor()
        # Vérifier que la tâche existe et que l'utilisateur est le créateur
        c.execute("SELECT task_image, created_by FROM custom_tasks WHERE id=?", (task_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            flash("Tâche personnalisée introuvable.", "danger")
            return redirect(url_for('categorie', cat=cat))
        task_image, created_by = row
        if created_by != session['user']:
            conn.close()
            flash("Tu ne peux supprimer que tes propres missions.", "danger")
            return redirect(url_for('categorie', cat=cat))

        # Supprimer l'image si présente
        if task_image:
            image_path = os.path.join('static', 'images', task_image)
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception:
                pass

        # Supprimer la tâche
        c.execute("DELETE FROM custom_tasks WHERE id=?", (task_id,))
        conn.commit()
        conn.close()
        flash("Mission personnalisée supprimée.", "success")
        return redirect(url_for('categorie', cat=cat))
from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date
import os
import random
import string
import base64
import uuid
import json
import requests

# Pour l'envoi de SMS (Twilio)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Twilio non installé. Installation: pip install twilio")

# WebSocket pour la synchronisation en temps réel
try:
    from flask_socketio import SocketIO, emit, join_room
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("⚠️ Flask-SocketIO non installé. Installation: pip3 install flask-socketio")



app = Flask(__name__)

def jinja2_index(lst, item):
    try:
        return lst.index(item)
    except ValueError:
        return -1
app.jinja_env.filters['index'] = jinja2_index

@app.errorhandler(500)
def handle_500(e):
    import traceback
    print(f"❌ ERREUR 500: {e}", flush=True)
    traceback.print_exc()
    return str(e), 500
app.secret_key = os.environ.get('SECRET_KEY', '2b7e4f8c-9a1d-4e2a-8c3e-7f5d1a2b9c4e-2025')

# 🔧 ProxyFix : indispensable sur Render (reverse proxy HTTPS)
# Sans ça, Flask génère des URLs http:// au lieu de https:// → cookies cassés, redirections folles
if os.environ.get('RENDER'):
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ⚡ Rechargement templates: True en local, False en prod (vérifie les fichiers à chaque render = lent)
app.config['TEMPLATES_AUTO_RELOAD'] = not bool(os.environ.get('RENDER'))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 604800  # 7 jours pour les fichiers statiques

# 🔥 DÉSACTIVER COMPLÈTEMENT LE CACHE JINJA2 (debug)
app.jinja_env.auto_reload = True
app.jinja_env.cache = {}

# � FORCER RECHARGEMENT TEMPLATE AVANT CHAQUE REQUÊTE
@app.before_request
def clear_template_cache():
    app.jinja_env.cache.clear()

# �🗜️ Compression gzip pour réduire la taille des réponses (~70% plus léger)
app.config['COMPRESS_LEVEL'] = 6          # Niveau de compression (1-9, 6 = bon équilibre vitesse/taille)
app.config['COMPRESS_MIN_SIZE'] = 500     # Ne pas compresser les petites réponses
app.config['COMPRESS_MIMETYPES'] = [
    'text/html', 'text/css', 'text/javascript',
    'application/javascript', 'application/json',
    'text/plain', 'application/x-javascript'
]
try:
    from flask_compress import Compress
    Compress(app)
    print("✅ Compression gzip activée")
except ImportError:
    print("⚠️ flask-compress non installé. Installation: pip install flask-compress")

# Ajouter un filtre Jinja personnalisé pour index
@app.template_filter('index')
def list_index_filter(lst, value):
    """Retourne l'index d'une valeur dans une liste"""
    try:
        return lst.index(value)
    except (ValueError, AttributeError):
        return 0

# Configuration des sessions pour qu'elles persistent après rafraîchissement
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Session valable 30 jours
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER') is not None  # True sur Render (HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ⚡ Cache in-memory pour inject_house_name (évite 1 requête DB par rendu)
_house_info_cache: dict = {}  # {email: {'name': ..., 'code': ..., 'ts': float}}


def _invalidate_house_cache(email: str):
    """Appeler quand le nom/code de la maison change (edit_house, etc.)"""
    _house_info_cache.pop(email, None)


def _log_login(email: str):
    """Enregistre une connexion dans login_logs pour le suivi bêta-testeurs."""
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO login_logs (email, ip) VALUES (?, ?)", (email, ip))
        conn.commit()
        conn.close()
    except Exception:
        pass

# Initialiser SocketIO si disponible
if SOCKETIO_AVAILABLE:
    # Configurer SocketIO — UNIQUEMENT gevent en production (plus d'eventlet)
    if os.environ.get('RENDER'):
        _async_mode = 'gevent'  # Forcé, pas de fallback
    else:
        _async_mode = 'threading'  # Local dev

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False,
        ping_timeout=60,      # Réduit de 120 à 60 secondes
        ping_interval=25,     # Réduit de 60 à 25 secondes
        async_mode=_async_mode,
        # Paramètres supplémentaires pour gunicorn + gevent
        engineio_options={
            'max_http_buffer_size': 1000000,  # 1MB buffer
            'transports': ['websocket', 'polling'],  # WebSocket en priorité
        }
    )
    print("✅ WebSocket activé pour la synchronisation en temps réel")
else:
    socketio = None
    print("⚠️ WebSocket désactivé - Flask-SocketIO non disponible")

# Enregistrer le blueprint pour la route de nommage de maison
app.register_blueprint(name_house_bp)

# Enregistrer la route de suppression personnalisée après la création de l'app
register_delete_custom_task_route(app)

# Rendre le nom de la maison disponible globalement dans les templates
@app.context_processor
def inject_house_name():
    house_name = None
    house_code = None
    try:
        if 'user' in session:
            email = session['user']
            now = time.time()
            cached = _house_info_cache.get(email)
            # Cache valide 2 minutes → évite 1 requête DB à chaque render de template
            if cached and (now - cached['ts']) < 120:
                return {'global_house_name': cached['name'], 'global_house_code': cached['code']}

            conn = get_db_connection()
            c = conn.cursor()
            # 🚀 OPTIMISATION: 1 seule requête avec JOIN au lieu de 2 requêtes séparées
            c.execute("""
                SELECT h.name, h.house_name, h.code 
                FROM users u JOIN houses h ON u.house_id = h.id 
                WHERE u.email=?
            """, (email,))
            hr = c.fetchone()
            if hr:
                name, house_name_db, code = hr[0], hr[1], hr[2]
                house_code = code
                if (house_name_db and house_name_db.strip()):
                    house_name = house_name_db.strip()
                elif (name and name.strip()):
                    house_name = name.strip()
            conn.close()
            # Mettre en cache + purge des entrées expirées (>600s)
            _house_info_cache[email] = {'name': house_name, 'code': house_code, 'ts': now}
            if len(_house_info_cache) > 200:
                expired = [k for k, v in _house_info_cache.items() if now - v['ts'] > 600]
                for k in expired:
                    del _house_info_cache[k]
    except Exception:
        pass
    return {
        'global_house_name': house_name,
        'global_house_code': house_code,
    }

# Thèmes de fond disponibles
BG_THEMES = {
    'marron':  'linear-gradient(135deg, #4a3428 0%, #1a1410 100%)',
    'bleu':    'linear-gradient(135deg, #A6D3DC 0%, #597176 100%)',
    'foret':   'linear-gradient(135deg, #1a3a2a 0%, #0d1f16 100%)',
    'nuit':    'linear-gradient(135deg, #1e1e3a 0%, #0d0d20 100%)',
    'ardoise': 'linear-gradient(135deg, #2c3e50 0%, #1a252f 100%)',
    'prune':   'linear-gradient(135deg, #3a1a2e 0%, #1a0d16 100%)',
    'sable':      'linear-gradient(135deg, #f0e4d0 0%, #d4b896 100%)',
    'menthe':     'linear-gradient(135deg, #c8e6d8 0%, #8cbfaa 100%)',
    'framboise':  'linear-gradient(135deg, #7a1f3f 0%, #3d0d1e 100%)',
    'rose':       'linear-gradient(135deg, #f9c2d4 0%, #e88aab 100%)',
    'peche':      'linear-gradient(135deg, #fdd9c8 0%, #f4a07a 100%)',
}

LIGHT_THEMES = {'bleu', 'sable', 'menthe', 'rose', 'peche'}

@app.context_processor
def inject_bg_theme():
    bg = BG_THEMES['bleu']
    theme_name = 'bleu'
    try:
        if 'user' in session:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT bg_theme FROM users WHERE email=?", (session['user'],))
            row = c.fetchone()
            conn.close()
            if row and row[0] and row[0] in BG_THEMES:
                theme_name = row[0]
                bg = BG_THEMES[theme_name]
    except Exception:
        pass
    is_light = theme_name in LIGHT_THEMES
    return {'bg_gradient': bg, 'bg_theme_name': theme_name, 'bg_theme_light': is_light}

# Filtre Jinja pour nettoyer l'intitulé des tâches à l'affichage
def clean_task(value: str) -> str:
    try:
        v = value or ''
        prefixes = [
            'Faire le ', 'Faire la ', 'Faire les ',
            'Passer l\'aspirateur ', 'Passer l\'aspirateur',
            'Ranger ', 'Nettoyer ', 'Changer ', 'Mettre ', 'Repasser ',
        ]
        for p in prefixes:
            if v.startswith(p):
                v = v[len(p):]
                break
        v = v.strip()
        # Réintroduire l'article pour certains noms
        lower = v.lower()
        article_map = {
            'café': 'le café',
            'vaisselle': 'la vaisselle',
            'courses': 'les courses',
            'lit': 'le lit',
            'linge': 'le linge',
            'aspirateur': "l'aspirateur",
            'surfaces': 'les surfaces',
            'machine': 'la machine',
            'toilettes': 'les toilettes',
            'lavabo': 'le lavabo',
            'douche': 'la douche',
            'miroir': 'le miroir',
            'garage': 'le garage',
            'outils': 'les outils',
            'chambre': 'la chambre',
            'chambre ado': 'la chambre ado',
            'chambre bébé': 'la chambre bébé',
            'zone ados': 'la zone ados',
            'bureau': 'le bureau',
            'buanderie': 'la buanderie',
            'cuisine': 'la cuisine',
            'salon': 'le salon',
        }
        if lower in article_map:
            # conserver la casse originale si possible
            return article_map[lower]
        return v
    except Exception:
        return value

app.jinja_env.filters['clean_task'] = clean_task

# Filtre Jinja: transformer un intitulé de tâche en phrase d'action au passé
def task_action(value: str) -> str:
    try:
        v = value or ''
        v = v.strip()
        # Cartographie des verbes -> participe passé
        verb_map = {
            'Faire': 'fait',
            'Passer': 'passé',
            'Ranger': 'rangé',
            'Nettoyer': 'nettoyé',
            'Changer': 'changé',
            'Mettre': 'mis',
            'Repasser': 'repassé',
            'Lancer': 'lancé',
            'Plier': 'plié',
            'Balayer': 'balayé',
        }
        # Extraire premier mot (verbe)
        parts = v.split(' ', 1)
        if not parts:
            return "a " + v
        verb = parts[0]
        rest = parts[1] if len(parts) > 1 else ''
        # Normaliser certains cas d'articles pour un rendu naturel
        # Si la tâche commence par "Faire le/la/les", on réintroduit l'article via clean_task
        if verb == 'Faire':
            noun = clean_task(v)
            return f"a fait {noun}"
        # Verbe connu -> participe passé
        pp = verb_map.get(verb)
        if pp:
            return f"a {pp} {rest}".strip()
        # Cas spécial aspirateur (souvent "Passer l'aspirateur")
        if "aspirateur" in v.lower():
            return "a passé l'aspirateur"
        # Sinon, fallback : "a fait" + contenu nettoyé
        return f"a fait {clean_task(v)}"
    except Exception:
        return f"a fait {value}"

app.jinja_env.filters['task_action'] = task_action

# Route pour la page Sats (Statistiques)
@app.route('/sats')
def sats():
    """
    Page de statistiques avec :
    - Podium des joueurs
    - Historique des tâches du jour par joueur avec heure
    - Détection des tentatives de triche
    - Compte à rebours jusqu'au dimanche (ouverture des cadeaux)
    """
    if 'user' not in session:
        return redirect(url_for('signup_email'))
    
    from datetime import date, datetime, timedelta
    import sqlite3
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Récupérer house_id de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            conn.close()
            flash("Crée ou rejoins une maison pour voir les statistiques ! 🏠", "info")
            return redirect(url_for('invite_partner'))
        
        house_id = row[0]
        today = date.today().isoformat()
        
        # ⚡ Vérifier et effectuer la réinitialisation hebdomadaire des statistiques si nécessaire
        check_weekly_reset(house_id, conn)
        
        # === RÉCUPÉRER LES JOUEURS DE LA MAISON ===
        c.execute("""
            SELECT email, name, avatar, avatar_url, avatar_file, points, avatar_style, player_color,
                   COALESCE(skull_count, 0), skull_expires_at, bonus_expires_at
            FROM users WHERE house_id=?
        """, (house_id,))
        users_rows = c.fetchall()
        
        players = []
        for u in users_rows:
            email, name, avatar_emoji, avatar_url, avatar_file, total_points, avatar_style, player_color_raw, skull_count, skull_expires_at_raw, bonus_expires_at_raw = u
            # Vérifier si le crâne est actif (malus ou tricherie prouvée)
            skull_active = False
            if skull_expires_at_raw:
                try:
                    skull_active = datetime.fromisoformat(str(skull_expires_at_raw)) > datetime.utcnow()
                except Exception:
                    pass
            # Vérifier si le bonus est actif
            bonus_active = False
            if bonus_expires_at_raw:
                try:
                    bonus_active = datetime.fromisoformat(str(bonus_expires_at_raw)) > datetime.utcnow()
                except Exception:
                    pass
            # Vérifier si le joueur est accusé (preuve en attente)
            c.execute("""SELECT COUNT(*) FROM proof_requests
                         WHERE target_email=? AND house_id=? AND status='pending'""",
                      (email, house_id))
            pending_row = c.fetchone()
            skull_pending = bool(pending_row and pending_row[0] > 0)
            
            # Vérifier si le joueur a une suspicion active (loupe 🔍)
            c.execute("""SELECT COUNT(*) FROM suspicions
                         WHERE suspected_player_email=? AND house_id=? 
                         AND status IN ('pending', 'awaiting_validation')""",
                      (email, house_id))
            suspicion_row = c.fetchone()
            suspicion_active = bool(suspicion_row and suspicion_row[0] > 0)
            suspicion_count = int(suspicion_row[0]) if suspicion_row else 0
            
            # Résoudre l'avatar : détection du type + reconstruction URL DiceBear
            resolved_avatar_file = None
            resolved_avatar_url = None
            resolved_avatar_emoji = None
            is_valid_emoji = False
            is_dicebear_seed = False
            
            # Détecter le type d'avatar dans le champ 'avatar'
            if avatar_emoji:
                avatar_str = str(avatar_emoji).strip()
                if (len(avatar_str) <= 4 and 
                    any(ord(c) > 127 for c in avatar_str) and
                    '.png' not in avatar_str.lower() and '.jpg' not in avatar_str.lower() and
                    'http' not in avatar_str.lower() and '/' not in avatar_str):
                    is_valid_emoji = True
                    resolved_avatar_emoji = avatar_str
                elif any(avatar_str.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    resolved_avatar_file = avatar_str
                elif (len(avatar_str) >= 2 and 
                      '.' not in avatar_str and 
                      'http' not in avatar_str.lower() and
                      '/' not in avatar_str):
                    is_dicebear_seed = True
            
            # 1. Si avatar_file est défini ET existe sur le disque, l'utiliser
            if avatar_file and avatar_file != 'None':
                validated = validate_avatar_file(avatar_file)
                if validated:
                    resolved_avatar_file = validated
            
            # 2. Si avatar_url est défini
            clean_avatar_url = avatar_url if avatar_url and avatar_url != 'None' else None
            
            # Extraction seed/style depuis l'URL si le champ avatar est vide
            if not avatar_emoji and clean_avatar_url and 'seed=' in clean_avatar_url:
                try:
                    import re
                    seed_match = re.search(r'seed=([^&]+)', clean_avatar_url)
                    if seed_match:
                        avatar_emoji = seed_match.group(1)
                        is_dicebear_seed = True
                    if not avatar_style:
                        style_match = re.search(r'dicebear\.com/[^/]+/([^/]+)/', clean_avatar_url)
                        if style_match:
                            avatar_style = style_match.group(1)
                except Exception:
                    pass
            
            # Si c'est un seed DiceBear, reconstruire l'URL avec le bon style
            if is_dicebear_seed and avatar_emoji:
                style = avatar_style if avatar_style else 'adventurer'
                resolved_avatar_url = f'https://api.dicebear.com/7.x/{style}/svg?seed={str(avatar_emoji).strip()}'
            elif clean_avatar_url:
                resolved_avatar_url = clean_avatar_url
            
            # Gérer les anciennes données incohérentes
            if resolved_avatar_file and (is_dicebear_seed or is_valid_emoji) and resolved_avatar_url:
                resolved_avatar_file = None
            
            # Si toujours rien → DiceBear par défaut
            if not resolved_avatar_file and not resolved_avatar_url and not resolved_avatar_emoji:
                seed = name if name else (email.split('@')[0] if email else 'default')
                style = avatar_style if avatar_style else 'adventurer'
                resolved_avatar_url = f'https://api.dicebear.com/7.x/{style}/svg?seed={seed}'
            
            # Points du jour
            c.execute("""
                SELECT COALESCE(SUM(points), 0), COUNT(*) 
                FROM completed_tasks 
                WHERE user_email=? AND DATE(completed_at)=?
            """, (email, today))
            daily = c.fetchone()
            daily_points = int(daily[0]) if daily[0] else 0
            daily_tasks = int(daily[1]) if daily[1] else 0
            
            # Points de la semaine (depuis lundi)
            week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
            c.execute("""
                SELECT COALESCE(SUM(points), 0), COUNT(*) 
                FROM completed_tasks 
                WHERE user_email=? AND DATE(completed_at) >= ?
            """, (email, week_start))
            weekly = c.fetchone()
            weekly_points = int(weekly[0]) if weekly[0] else 0
            weekly_tasks = int(weekly[1]) if weekly[1] else 0
            
            # Points du mois (depuis le 1er du mois)
            month_start = date.today().replace(day=1).isoformat()
            c.execute("""
                SELECT COALESCE(SUM(points), 0), COUNT(*) 
                FROM completed_tasks 
                WHERE user_email=? AND DATE(completed_at) >= ?
            """, (email, month_start))
            monthly = c.fetchone()
            monthly_points = int(monthly[0]) if monthly[0] else 0
            monthly_tasks = int(monthly[1]) if monthly[1] else 0
            
            # Progression hebdomadaire sur les 4 dernières semaines
            weekly_progression = []
            for week_offset in range(4, 0, -1):
                week_start_offset = (date.today() - timedelta(days=date.today().weekday() + (week_offset - 1) * 7)).isoformat()
                week_end_offset = (date.today() - timedelta(days=date.today().weekday() + (week_offset - 2) * 7)).isoformat()
                c.execute("""
                    SELECT COALESCE(SUM(points), 0)
                    FROM completed_tasks 
                    WHERE user_email=? AND DATE(completed_at) >= ? AND DATE(completed_at) < ?
                """, (email, week_start_offset, week_end_offset))
                week_points = c.fetchone()
                weekly_progression.append(int(week_points[0]) if week_points and week_points[0] else 0)
            
            # Détails des tâches de la semaine pour ce joueur
            c.execute("""
                SELECT task_name, points, category
                FROM completed_tasks 
                WHERE user_email=? AND DATE(completed_at) >= ?
                ORDER BY completed_at DESC
                LIMIT 20
            """, (email, week_start))
            tasks_details_rows = c.fetchall()
            weekly_tasks_details = [
                {
                    'name': t[0],
                    'points': t[1],
                    'room': t[2] if t[2] else 'Autre'
                }
                for t in tasks_details_rows
            ]
            
            # Récupérer ou attribuer la couleur du joueur
            p_color = player_color_raw if player_color_raw else get_player_color(email)
            
            players.append({
                'email': email,
                'name': name if name else email.split('@')[0],
                'avatar': resolved_avatar_emoji,  # Emoji direct si valide
                'avatar_url': resolved_avatar_url,  # URL si présente
                'avatar_file': resolved_avatar_file,  # Fichier (uploadé ou PNG prédéfini)
                'avatar_style': avatar_style if avatar_style else 'adventurer',  # Style DiceBear
                'total_points': total_points if total_points else 0,
                'daily_points': daily_points,
                'daily_tasks': daily_tasks,
                'weekly_points': weekly_points,
                'weekly_tasks': weekly_tasks,
                'monthly_points': monthly_points,
                'monthly_tasks': monthly_tasks,
                'weekly_progression': weekly_progression,
                'weekly_tasks_details': weekly_tasks_details,
                'is_current_user': (email == session['user']),
                'color': p_color,  # Couleur identitaire du joueur
                'skull_count': int(skull_count) if skull_count else 0,
                'skull_active': skull_active,    # Crâne actif (malus ou tricherie prouvée)
                'skull_pending': skull_pending,  # Crâne suspicion (accusation en cours)
                'bonus_active': bonus_active,    # Cœur actif (bonus reçu il y a moins d'1h)
                'suspicion_active': suspicion_active,  # Loupe active (suspicion en attente)
                'suspicion_count': suspicion_count,    # Nombre de suspicions actives
            })
        
        # Trier par points de la semaine (pour le classement général et le leader)
        # Le template fera le tri par daily_points pour le podium du jour
        players.sort(key=lambda x: x['weekly_points'], reverse=True)
        
        # Attribuer les rangs
        for idx, p in enumerate(players, start=1):
            p['rank'] = idx
        
        # === COULEURS DE GRAPHIQUE (cohérentes avec les barres de progression du menu) ===
        # Même logique que menu.html : player_color DB (hex) en priorité, sinon palette index email
        _CHART_PALETTE = [
            'rgba(120,180,230,0.8)', 'rgba(180,140,200,0.8)', 'rgba(240,140,140,0.8)',
            'rgba(250,180,100,0.8)', 'rgba(130,200,150,0.8)', 'rgba(240,150,170,0.8)',
            'rgba(120,210,200,0.8)', 'rgba(255,170,170,0.8)', 'rgba(140,220,210,0.8)',
            'rgba(255,200,120,0.8)',
        ]
        _sorted_emails_colors = sorted([p['email'] for p in players])
        for p in players:
            _idx = _sorted_emails_colors.index(p['email']) if p['email'] in _sorted_emails_colors else 0
            _hex = p.get('color')  # Hex DB (ex: '#FF6B9D')
            if _hex and _hex.startswith('#') and len(_hex) >= 7:
                try:
                    _r = int(_hex[1:3], 16)
                    _g = int(_hex[3:5], 16)
                    _b = int(_hex[5:7], 16)
                    p['chart_color'] = f'rgba({_r},{_g},{_b},0.8)'
                    p['chart_border'] = f'rgba({_r},{_g},{_b},1)'
                except Exception:
                    p['chart_color'] = _CHART_PALETTE[_idx % len(_CHART_PALETTE)]
                    p['chart_border'] = _CHART_PALETTE[_idx % len(_CHART_PALETTE)].replace('0.8', '1')
            else:
                p['chart_color'] = _CHART_PALETTE[_idx % len(_CHART_PALETTE)]
                p['chart_border'] = _CHART_PALETTE[_idx % len(_CHART_PALETTE)].replace('0.8', '1')
        
        # Trouver l'utilisateur actuel dans la liste des joueurs
        current_user_data = None
        for p in players:
            if p['email'] == session['user']:
                current_user_data = p
                break
        
        # === RÉCUPÉRER L'HISTORIQUE DES TÂCHES DU JOUR ===
        c.execute("""
            SELECT 
                ct.user_email,
                ct.task_name,
                ct.points,
                ct.completed_at,
                ct.category,
                u.name,
                u.avatar_url,
                u.avatar_file
            FROM completed_tasks ct
            LEFT JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ?
              AND DATE(ct.completed_at) = ?
            ORDER BY ct.completed_at DESC
        """, (house_id, today))
        
        tasks_rows = c.fetchall()
        tasks_history = []
        
        for t in tasks_rows:
            email, task_name, points, completed_at, category, name, avatar_url, avatar_file = t
            
            # Résoudre l'avatar
            valid_file = validate_avatar_file(avatar_file)
            if valid_file:
                avatar = url_for('static', filename=f'avatars/{valid_file}')
            elif avatar_url:
                avatar = avatar_url
            else:
                avatar = f'https://api.dicebear.com/7.x/adventurer/svg?seed={name or email}'
            
            # Extraire l'heure (compatible str ISO et objet datetime)
            try:
                if hasattr(completed_at, 'strftime'):
                    time_str = completed_at.strftime('%H:%M')
                else:
                    completed_at_str = str(completed_at or '')
                    dt = datetime.fromisoformat(completed_at_str.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
            except Exception:
                completed_at_str = str(completed_at or '')
                if ' ' in completed_at_str:
                    time_str = completed_at_str.split(' ')[1][:5]
                elif 'T' in completed_at_str:
                    time_str = completed_at_str.split('T')[1][:5]
                else:
                    time_str = '??:??'
            
            tasks_history.append({
                'email': email,
                'player_name': name if name else email.split('@')[0],
                'avatar': avatar,
                'task_name': task_name,
                'points': points,
                'time': time_str,
                'category': category,
                'is_current_user': (email == session['user'])
            })
        
        # === DÉTECTER LES TENTATIVES DE TRICHE ===
        # Définition: plus de 3 validations de la même tâche en une journée
        c.execute("""
            SELECT 
                user_email,
                task_name,
                COUNT(*) as attempts
            FROM completed_tasks
            WHERE house_id = ?
              AND DATE(completed_at) = ?
            GROUP BY user_email, task_name
            HAVING COUNT(*) > 1
        """, (house_id, today))
        
        suspicious_rows = c.fetchall()
        cheating_attempts = []
        
        for s in suspicious_rows:
            email, task_name, attempts = s
            # Trouver le nom du joueur
            player_name = email.split('@')[0]
            for p in players:
                if p['email'] == email:
                    player_name = p['name']
                    break
            
            cheating_attempts.append({
                'player_name': player_name,
                'task_name': task_name,
                'attempts': attempts
            })
        
        # === COMPTE À REBOURS JUSQU'AU DIMANCHE ===
        today_date = date.today()
        days_until_sunday = (6 - today_date.weekday()) % 7
        if days_until_sunday == 0:
            countdown_text = "C'est dimanche ! 🎁"
            is_sunday = True
        else:
            countdown_text = f"{days_until_sunday} jour{'s' if days_until_sunday > 1 else ''}"
            is_sunday = False
        
        # === RÉCUPÉRER LE NOM DE LA MAISON ===
        c.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
        house_row = c.fetchone()
        house_name = None
        if house_row:
            house_name = house_row[0] if house_row[0] else house_row[1]
        
        # === RÉCUPITULATIF PAR PIÈCE ===
        # Mapping des images par pièce
        ROOM_IMAGES = {
            'salon': 'images/cuisine.png',  # Utiliser une image par défaut
            'cuisine': 'images/cuisine.png',
            'buanderie': 'images/buanderie.png',
            'toilettes': 'images/toilettes.jpg',
            'chambre': 'images/lit.png',
            'chambre_parentale': 'images/lit.png',
            'salle_bain': 'images/toilettes.jpg',
            'salle_de_bain': 'images/toilettes.jpg',
            'chambre_enfant': 'images/chambre enfant.webp',
            'chambre_bebe': 'images/chambre bébé.webp',
            'chambre_ado': 'images/chambre ado.webp',
            'piece_bonus': 'images/debarras.webp',
            'garage': 'images/carwash.webp',
        }
        
        # Mapping des noms et icônes de pièces
        ROOM_NAMES = {
            'salon': ('Salon', '🛋️'),
            'cuisine': ('Cuisine', '🍳'),
            'buanderie': ('Buanderie', '👕'),
            'toilettes': ('Toilettes', '🚽'),
            'chambre': ('Chambre', '🛏️'),
            'chambre_parentale': ('Chambre', '🛏️'),
            'salle_bain': ('Salle de bain', '🛁'),
            'salle_de_bain': ('Salle de bain', '🛁'),
            'chambre_enfant': ('Chambre Enfant', '🧸'),
            'chambre_bebe': ('Chambre Bébé', '👶'),
            'chambre_ado': ('Zone Ados', '🎮'),
            'piece_bonus': ('Bureau', '🖥️'),
            'garage': ('Garage', '🚗'),
        }
        
        # Récupérer les tâches du jour par pièce avec détails
        c.execute("""
            SELECT 
                ct.category,
                ct.task_name,
                ct.points,
                ct.user_email,
                u.name as user_name
            FROM completed_tasks ct
            LEFT JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ?
              AND DATE(ct.completed_at) = ?
            ORDER BY ct.category, ct.completed_at DESC
        """, (house_id, today))
        
        room_tasks_rows = c.fetchall()
        
        # Organiser par pièce
        rooms_recap = {}
        for row in room_tasks_rows:
            category, task_name, points, user_email, user_name = row
            if not category:
                category = 'autre'
            
            if category not in rooms_recap:
                room_name, room_icon = ROOM_NAMES.get(category, (category.replace('_', ' ').title(), '🏠'))
                room_image = ROOM_IMAGES.get(category, 'images/maisonwoop.svg')
                rooms_recap[category] = {
                    'name': room_name,
                    'icon': room_icon,
                    'image': room_image,
                    'task_count': 0,
                    'total_points': 0,
                    'tasks': []
                }
            
            player_display = user_name if user_name else (user_email.split('@')[0] if user_email else 'Inconnu')
            rooms_recap[category]['task_count'] += 1
            rooms_recap[category]['total_points'] += points if points else 0
            rooms_recap[category]['tasks'].append({
                'name': task_name,
                'points': points,
                'player': player_display
            })
        
        # Convertir en liste triée par nombre de tâches
        rooms_list = sorted(rooms_recap.values(), key=lambda x: x['task_count'], reverse=True)
        
        # === RÉCUPÉRER LES TÂCHES DE LA SEMAINE POUR LE CAMEMBERT ===
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        c.execute("""
            SELECT category, COUNT(*) as count
            FROM completed_tasks
            WHERE house_id = ?
              AND DATE(completed_at) >= ?
            GROUP BY category
            ORDER BY count DESC
        """, (house_id, week_start))
        
        weekly_tasks_by_room = []
        for row in c.fetchall():
            category, count = row
            if category:
                weekly_tasks_by_room.append({
                    'category': category,
                    'count': count
                })
        
        conn.close()
        
        return render_template('sats.html',
            players=players,
            tasks_history=tasks_history,
            weekly_tasks_by_room=weekly_tasks_by_room,
            cheating_attempts=cheating_attempts,
            countdown_text=countdown_text,
            days_until_sunday=days_until_sunday,
            is_sunday=is_sunday,
            house_name=house_name,
            current_user=current_user_data,
            rooms_recap=rooms_list,
            menu_page=True
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        _dbg(f"\n{'='*60}")
        _dbg(f"❌ ERREUR PAGE STATS (/sats)")
        _dbg(f"{'='*60}")
        _dbg(f"Exception: {e}")
        _dbg(f"Type: {type(e).__name__}")
        _dbg(f"\nTraceback complet:")
        _dbg(error_details)
        _dbg(f"{'='*60}\n")
        conn.close()
        flash(f"Erreur lors du chargement des stats: {e}", "error")
        return redirect(url_for('menu'))


# Route pour la page de statistiques avec graphiques
@app.route('/stats_graphique')
def stats_graphique():
    """Page de statistiques avec graphiques détaillés"""
    if 'user' not in session:
        return redirect(url_for('signup_email'))
    
    from datetime import date, datetime, timedelta
    import sqlite3
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Récupérer house_id de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            conn.close()
            flash("Crée ou rejoins une maison pour voir les statistiques ! 🏠", "info")
            return redirect(url_for('invite_partner'))
        
        house_id = row[0]
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        
        # ⚡ Vérifier et effectuer la réinitialisation hebdomadaire des statistiques si nécessaire
        check_weekly_reset(house_id, conn)
        
        # === DONNÉES POUR GRAPHIQUE 1: Évolution des points sur 7 jours ===
        daily_points_labels = []
        daily_points_values = []
        
        for i in range(7):
            day = today - timedelta(days=6-i)
            day_name = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][day.weekday()]
            daily_points_labels.append(day_name)
            
            c.execute("""
                SELECT COALESCE(SUM(points), 0)
                FROM completed_tasks
                WHERE user_email=? AND DATE(completed_at)=?
            """, (session['user'], day.isoformat()))
            points = c.fetchone()[0]
            daily_points_values.append(int(points) if points else 0)
        
        # === DONNÉES POUR GRAPHIQUE 2: Comparaison joueurs ===
        c.execute("""
            SELECT u.name, u.email, COALESCE(SUM(ct.points), 0) as total_points
            FROM users u
            LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                AND DATE(ct.completed_at) >= ?
            WHERE u.house_id = ?
            GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style
            ORDER BY total_points DESC
            LIMIT 5
        """, (week_start, house_id))
        
        players_rows = c.fetchall()
        players_labels = [row[0] if row[0] else row[1].split('@')[0] for row in players_rows]
        players_values = [int(row[2]) for row in players_rows]
        
        # === DONNÉES POUR GRAPHIQUE 3: Répartition par catégorie ===
        c.execute("""
            SELECT category, COUNT(*) as count
            FROM completed_tasks
            WHERE house_id = ? AND DATE(completed_at) >= ?
            GROUP BY category
            ORDER BY count DESC
            LIMIT 6
        """, (house_id, week_start))
        
        categories_rows = c.fetchall()
        categories_labels = [row[0] if row[0] else 'Autre' for row in categories_rows]
        categories_values = [int(row[1]) for row in categories_rows]
        
        # === DONNÉES POUR GRAPHIQUE 4: Performance par jour de la semaine ===
        weekday_values = []
        for weekday in range(7):
            c.execute("""
                SELECT COUNT(*)
                FROM completed_tasks
                WHERE user_email=? 
                AND CAST(strftime('%w', DATE(completed_at)) AS INTEGER) = ?
            """, (session['user'], weekday))
            count = c.fetchone()[0]
            # Dimanche (0) en dernier
            weekday_values.append(int(count) if count else 0)
        
        # Réorganiser pour que lundi soit en premier
        weekday_values = weekday_values[1:] + [weekday_values[0]]
        
        # === CALCULS STATISTIQUES ===
        # Points totaux de la semaine
        c.execute("""
            SELECT COALESCE(SUM(points), 0)
            FROM completed_tasks
            WHERE user_email=? AND DATE(completed_at) >= ?
        """, (session['user'], week_start))
        total_weekly_points = int(c.fetchone()[0] or 0)
        
        # Tâches totales de la semaine
        c.execute("""
            SELECT COUNT(*)
            FROM completed_tasks
            WHERE user_email=? AND DATE(completed_at) >= ?
        """, (session['user'], week_start))
        total_weekly_tasks = int(c.fetchone()[0] or 0)
        
        # Moyenne par jour
        avg_daily_points = round(total_weekly_points / 7, 1) if total_weekly_points > 0 else 0
        
        # Classement
        c.execute("""
            SELECT u.email, COALESCE(SUM(ct.points), 0) as total_points
            FROM users u
            LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                AND DATE(ct.completed_at) >= ?
            WHERE u.house_id = ?
            GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style
            ORDER BY total_points DESC
        """, (week_start, house_id))
        
        ranking = c.fetchall()
        rank = None
        for idx, (email, points) in enumerate(ranking, 1):
            if email == session['user']:
                if idx == 1:
                    rank = "🥇"
                elif idx == 2:
                    rank = "🥈"
                elif idx == 3:
                    rank = "🥉"
                else:
                    rank = f"{idx}e"
                break
        
        conn.close()
        
        return render_template('stats_graphique.html',
            daily_points_data={'labels': daily_points_labels, 'data': daily_points_values},
            players_data={'labels': players_labels, 'data': players_values},
            categories_data={'labels': categories_labels, 'data': categories_values},
            weekday_data={'data': weekday_values},
            total_weekly_points=total_weekly_points,
            total_weekly_tasks=total_weekly_tasks,
            avg_daily_points=avg_daily_points,
            rank=rank,
            menu_page=True
        )
        
    except Exception as e:
        import traceback
        _dbg(f"Erreur page stats graphique: {e}")
        _dbg(traceback.format_exc())
        conn.close()
        return redirect(url_for('sats'))


# ...existing code...

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date
import os
import random
import string
import base64
import uuid
import json
import requests
import socket
# Pour l'envoi de SMS (Twilio)

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Twilio non installé. Installation: pip install twilio")



# Route d'accueil
@app.route('/')
def index():
    """Page d'accueil - Redirection vers la page de bienvenue"""
    # Si l'utilisateur est déjà connecté, le rediriger vers le menu
    if 'user' in session:
        return redirect(url_for('menu'))
    # Sinon, afficher la page de bienvenue
    return redirect(url_for('welcome'))

@app.route('/test_audio')
def test_audio():
    return render_template('test_audio.html')

@app.route('/test_audio_mobile')
def test_audio_mobile():
    return render_template('test_audio_mobile.html')

@app.route('/test_images_mobile')
def test_images_mobile():
    return render_template('test_images_mobile.html')

@app.route('/clear_cache')
def clear_cache():
    return render_template('clear_cache.html')

@app.route('/test_menu_simple')
def test_menu_simple():
    return render_template('test_menu_simple.html')

@app.route('/test_invitation')
def test_invitation():
    # Lire et afficher le fichier HTML de test
    try:
        with open('test_invitation.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except:
        return "Erreur lors du chargement de la page de test"

@app.route('/test_baby_api')
def test_baby_api():
    # Servir le fichier de test baby API
    try:
        with open('test_baby_api.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except:
        return "Erreur lors du chargement de la page de test baby API"

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')


# Route de compatibilité pour templates pointant sur 'signup'
@app.route('/signup')
def signup():
    """Point d'entrée d'inscription générique (redirige vers le choix d'inscription)"""
    # Si vous préférez afficher une page de choix d'inscription, utilisez 'signup.html'
    try:
        return render_template('signup.html')
    except Exception:
        return redirect(url_for('signup_email'))


# Routes de placeholder pour intégrations sociales mentionnées dans les templates
@app.route('/signup_facebook')
def signup_facebook():
    # Placeholder minimal: redirige vers l'inscription par email
    flash("Inscription via Facebook non configurée. Utilisez l'inscription par email.", "info")
    return redirect(url_for('signup_email'))


@app.route('/signup_google')
def signup_google():
    # Placeholder minimal: redirige vers l'inscription par email
    flash("Inscription via Google non configurée. Utilisez l'inscription par email.", "info")
    return redirect(url_for('signup_email'))


@app.route('/home')
def home():
    """Alias simple pour la page d'accueil (certaines templates utilisent 'home')."""
    return redirect(url_for('welcome'))

# Configuration pour l'upload de fichiers
UPLOAD_FOLDER = 'static/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# Configuration SMS Twilio (remplacez par vos vraies clés)
TWILIO_ACCOUNT_SID = 'your_account_sid_here'
TWILIO_AUTH_TOKEN = 'your_auth_token_here' 
TWILIO_PHONE_NUMBER = '+1234567890'  # Votre numéro Twilio

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

# Nombre maximum de joueurs par maison. Mettre à `None` pour illimité.
MAX_PLAYERS = None

# ===============================
# CONNEXION SQLITE OPTIMISÉE
# ===============================

def get_db_connection(timeout=30.0):
    """
    Connexion DB unifiée : SQLite en local, PostgreSQL sur Render.
    Retourne un _CompatConn compatible avec l'API sqlite3.
    ⚠️ Connexions directes PostgreSQL (pas de pool pour compatibilité gevent/eventlet)
    """
    if _USE_PG:
        # Connexion directe PostgreSQL (compatible gevent/eventlet)
        for attempt in range(3):
            try:
                conn = psycopg2.connect(_PG_URL, connect_timeout=10)
                conn.autocommit = False
                return _CompatConn(conn, is_pg=True)
            except Exception as e:
                if attempt < 2:
                    import time; time.sleep(0.5)
                else:
                    raise
    else:
        raw = sqlite3.connect(DB, timeout=timeout, check_same_thread=False)
        # Optimisations SQLite
        raw.execute('PRAGMA journal_mode=WAL')
        raw.execute('PRAGMA synchronous=NORMAL')
        raw.execute('PRAGMA cache_size=10000')
        raw.execute('PRAGMA temp_store=MEMORY')
        return _CompatConn(raw, is_pg=False)

# ===============================
# RÉINITIALISATION HEBDOMADAIRE
# ===============================

def check_weekly_reset(house_id, conn=None):
    """
    Vérifie et effectue la réinitialisation hebdomadaire des statistiques.
    - Supprime les tâches complétées de la semaine précédente (plus de 7 jours)
    - Se déclenche le lundi matin (début de nouvelle semaine)
    - Garde seulement les tâches de la semaine en cours
    
    Paramètres:
        house_id: ID de la maison
        conn: Connexion DB existante (optionnelle, sinon en crée une)
    
    Retour:
        True si une réinitialisation a été effectuée, False sinon
    """
    from datetime import date, timedelta
    
    should_close = False
    if not conn:
        conn = get_db_connection()
        should_close = True
    
    c = conn.cursor()
    reset_performed = False
    
    try:
        today = date.today()
        current_week_start = (today - timedelta(days=today.weekday())).isoformat()  # Lundi de cette semaine
        
        # Récupérer la date de dernière réinitialisation hebdomadaire
        c.execute("SELECT last_weekly_reset_date FROM houses WHERE id=?", (house_id,))
        row = c.fetchone()
        
        last_weekly_reset = row[0] if row and row[0] else None
        
        # Si on n'a jamais fait de reset hebdomadaire, ou si le dernier reset date d'avant cette semaine
        if not last_weekly_reset or last_weekly_reset < current_week_start:
            # On est dans une nouvelle semaine, réinitialiser les statistiques
            
            # Supprimer les tâches complétées de la semaine précédente (avant le lundi de cette semaine)
            c.execute("""
                DELETE FROM completed_tasks 
                WHERE house_id=? AND DATE(completed_at) < ?
            """, (house_id, current_week_start))
            
            deleted_count = c.rowcount
            
            # Mettre à jour la date de dernière réinitialisation hebdomadaire
            c.execute("UPDATE houses SET last_weekly_reset_date=? WHERE id=?", 
                     (current_week_start, house_id))
            
            conn.commit()
            reset_performed = True
            
            _dbg(f"✅ Réinitialisation hebdomadaire effectuée pour house_id={house_id}: {deleted_count} tâches archivées")
        
    except Exception as e:
        _dbg(f"❌ Erreur lors de la réinitialisation hebdomadaire: {e}")
        if conn:
            conn.rollback()
    finally:
        if should_close and conn:
            conn.close()
    
    return reset_performed

# ===============================
# FONCTIONS UTILITAIRES
# ===============================

def allowed_file(filename):
    """Vérifie si le fichier est autorisé"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_photo_from_base64(base64_data):
    """Compresse une photo base64 et retourne un data URI pour stockage en DB.
    Ne crée aucun fichier sur disque — compatible avec Render (filesystem éphémère)."""
    try:
        header, data = base64_data.split(',', 1)
        image_data = base64.b64decode(data)

        # Compresser avec Pillow si disponible (max 400×400, qualité 75)
        try:
            from PIL import Image
            import io as _io
            img = Image.open(_io.BytesIO(image_data)).convert('RGB')
            img.thumbnail((400, 400), Image.LANCZOS)
            buf = _io.BytesIO()
            img.save(buf, format='JPEG', quality=75, optimize=True)
            image_data = buf.getvalue()
        except ImportError:
            pass  # Pillow absent : utiliser les données brutes

        compressed_b64 = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/jpeg;base64,{compressed_b64}"
    except Exception as e:
        _dbg(f"Erreur traitement photo: {e}")
        return None

def get_avatar_url(avatar_id, style='adventurer'):
    """Retourne l'URL de l'avatar basé sur l'ID avec DiceBear du style donné"""
    seeds = [
        'default', 'alice', 'bella', 'chloe', 'diana', 'emma',
        'fiona', 'grace', 'hannah', 'iris', 'julia', 'kate'
    ]
    
    try:
        seed = seeds[int(avatar_id)]
    except (ValueError, IndexError):
        seed = seeds[0]
    
    return f'https://api.dicebear.com/7.x/{style}/svg?seed={seed}'

def send_sms_invitation(phone_number, user_name, house_code=None):
    """Envoie un SMS d'invitation"""
    # Obtenir l'URL de base depuis le contexte de la requête Flask
    base_url = request.host_url if has_request_context() else "http://192.168.1.187:8000/"
    
    if not TWILIO_AVAILABLE:
        if house_code:
            _dbg(f"\n📱 SMS simulé envoyé vers {phone_number}:")
            _dbg(f"   🏠 {user_name} vous invite à jouer à Dust !")
            _dbg(f"   📱 Cliquez pour rejoindre (aucune installation requise) :")
            _dbg(f"   {base_url}invite/{house_code}")
            _dbg(f"   Code : {house_code}\n")
        else:
            _dbg(f"SMS simulé vers {phone_number}: {user_name} vous invite à jouer à Dust !")
            _dbg(f"📱 Cliquez : {base_url}")
        return True
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        if house_code:
            message_body = f"🏠 {user_name} vous invite à jouer à 'Dust' ! " \
                          f"📱 Cliquez pour rejoindre (aucune installation requise) : " \
                          f"{base_url}invite/{house_code} " \
                          f"Code : {house_code}"
        else:
            message_body = f"🏠 {user_name} vous invite à jouer à 'Dust' ! " \
                          f"📱 Cliquez pour commencer : {base_url}"
        
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        _dbg(f"SMS envoyé avec succès: {message.sid}")
        return True
        
    except Exception as e:
        _dbg(f"Erreur envoi SMS: {e}")
        return False

# ===============================
# CONFIGURATION DES TÂCHES
# ===============================
# Structure centralisée pour faciliter l'ajout de nouvelles tâches
# Pour ajouter une nouvelle tâche, ajoutez simplement une entrée dans TASKS_CONFIG
TASKS_CONFIG = {
    'cuisine': [
        {
            'name': 'Faire le café',
            'image': 'cuisine/cafe.png',
            'description': 'Commence ta journée avec un bon café !',
            'points': 3,
            'fun_text': 'Allez, un petit café… sinon je me rendors pour la journée !',
            'ad_text': 'Le secret d\'un bon café ? Une machine bien entretenue et des grains frais !',
            'ad_link': 'https://www.nespresso.com/fr/fr'
        },
        {
            'name': 'Faire les courses',
            'image': 'cuisine/faire_course.png',
            'description': 'N\'oublie rien sur ta liste !',
            'points': 8,
            'fun_text': '🛒 Caddie en main, liste en tête... C\'est parti pour l\'aventure !',
            'ad_text': 'Astuce budget : fais ta liste par rayon pour éviter les achats impulsifs !',
            'ad_link': 'https://www.carrefour.fr/'
        },
        {
            'name': 'Faire à manger',
            'image': 'cuisine/faire à manger.webp',
            'description': 'Prépare un bon repas pour toute la famille !',
            'points': 10,
            'fun_text': '👨‍🍳 Aux fourneaux chef ! La brigade attend son repas !',
            'ad_text': 'Batch cooking : cuisine tes repas de la semaine le dimanche, tu gagnes 1h par jour !',
            'ad_link': 'https://www.marmiton.org/'
        },
        {
            'name': 'Mettre la table',
            'image': 'cuisine/mettre la table.webp',
            'description': 'Dresse une belle table pour le repas !',
            'points': 3,
            'fun_text': '🍽️ Assiettes, couverts, serviettes... On met les petits plats dans les grands !',
            'ad_text': 'Astuce déco : un set de table coloré et des serviettes assorties, ça change tout !',
            'ad_link': 'https://www.ikea.com/fr/fr/cat/arts-de-la-table-24070/'
        },
        {
            'name': 'Mettre dans le lave-vaisselle',
            'image': 'cuisine/lave vaiselle.webp',
            'description': 'Range la vaisselle sale dans le lave-vaisselle !',
            'points': 4,
            'fun_text': '🍽️ Tetris version vaisselle : optimise l\'espace !',
            'ad_text': 'Lance ton lave-vaisselle le soir en heures creuses, tu économises jusqu\'à 30% !',
            'ad_link': 'https://www.amazon.fr/s?k=tablettes+lave+vaisselle'
        },
        {
            'name': 'Passer l\'éponge',
            'image': 'cuisine/passer l\'eponge.webp',
            'description': 'Nettoie les surfaces et la table !',
            'points': 4,
            'fun_text': '🧽 Frotte, frotte ! On efface les traces du festin !',
            'ad_text': 'Change ton éponge toutes les semaines pour éviter les bactéries !',
            'ad_link': 'https://www.amazon.fr/s?k=eponge+ecologique'
        },
        {
            'name': 'Nettoyer le plan de travail',
            'image': 'cuisine/nettoyer le plan de travil.webp',
            'description': 'Des plans de travail impeccables !',
            'points': 4,
            'fun_text': '✨ Un plan de travail nickel, c\'est la base d\'une cuisine pro !',
            'ad_text': 'Bicarbonate + citron = le combo magique pour dégraisser sans produits chimiques !',
            'ad_link': 'https://www.amazon.fr/s?k=produits+entretien+naturel'
        },
        {
            'name': 'Ranger la vaisselle',
            'image': 'cuisine/ranger la vaiselle.webp',
            'description': 'Range la vaisselle propre dans les placards !',
            'points': 4,
            'fun_text': '📦 Chaque chose à sa place, et une place pour chaque chose !',
            'ad_text': 'Organise tes placards par zone d\'usage : gain de temps assuré !',
            'ad_link': 'https://www.ikea.com/fr/fr/cat/rangement-cuisine-24796/'
        },
        {
            'name': 'Livraison',
            'image': 'cuisine/livraisonUber.webp',
            'description': 'Commande ou réceptionne une livraison de repas !',
            'points': -3,
            'fun_text': '🚴 Ding dong ! Le resto vient à toi ce soir !',
            'ad_text': 'Astuce budget : compare les prix entre Uber Eats, Deliveroo et Just Eat !',
            'ad_link': 'https://www.ubereats.com/fr'
        }
    ],
    'buanderie': [
        {
            'name': 'Laver son linge',
            'image': 'buanderie/machine.jpg',
            'description': 'Lancer une machine de linge',
            'points': 4,
            'fun_text': '🧺 Trie bien tes couleurs, sinon gare aux chaussettes roses !',
            'ad_text': '30° suffisent pour 90% du linge ! Tu économises de l\'énergie et tes vêtements durent plus longtemps.',
            'ad_link': 'https://www.amazon.fr/s?k=lessive+ecologique'
        },
        {
            'name': 'Sécher son linge',
            'image': 'buanderie/linge etendu.webp',
            'description': 'Étendre ou sécher le linge',
            'points': 3,
            'fun_text': '🌞 Le soleil est le meilleur sèche-linge !',
            'ad_text': 'Le séchage à l\'air libre préserve tes vêtements et économise de l\'énergie.',
            'ad_link': 'https://www.amazon.fr/s?k=etendoir+linge'
        },
        {
            'name': 'Plier son linge',
            'image': 'buanderie/linge plié.webp',
            'description': 'Plier le linge propre',
            'points': 4,
            'fun_text': '👕 Marie Kondo serait fière de toi !',
            'ad_text': 'La méthode KonMari : plie tes t-shirts en rectangle et range-les à la verticale. Tu verras tout d\'un coup d\'œil !',
            'ad_link': 'https://www.youtube.com/watch?v=K2VljzCC16g'
        },
        {
            'name': 'Ranger ses vêtements',
            'image': 'buanderie/ranger ses vetements.webp',
            'description': 'Ranger les vêtements dans l\'armoire',
            'points': 3,
            'fun_text': '🗄️ Une place pour chaque chose, chaque chose à sa place !',
            'ad_text': 'Organisateurs de tiroirs : trouve ce que tu cherches en 2 secondes !',
            'ad_link': 'https://www.amazon.fr/s?k=organisateur+tiroir'
        }
    ],
    'toilettes': [
        {
            'name': 'Nettoyer les toilettes',
            'image': 'wc/laver_toillettes.webp',
            'description': '🚽 Nettoyer des toilettes ça vaut des points, personne n\'aime laver les chiottes… 😉 !',
            'points': 6,
            'fun_text': '🚽 Le trône mérite un peu d\'attention royale !',
            'ad_text': 'Verse un verre de coca dans la cuvette, laisse agir 1h : détartrage express et naturel !',
            'ad_link': 'https://www.amazon.fr/s?k=produits+toilettes'
        },
        {
            'name': 'Changer le rouleau de papier toilette',
            'image': 'wc/jeter_rouleaux.png',
            'description': '🧻 Tu peux jeter les rouleaux ou en faire des ronds de serviettes ! 😄',
            'points': 2,
            'fun_text': '🧻 Le héros silencieux de la maison !',
            'ad_text': 'Le saviez-vous ? Le papier recyclé est tout aussi doux et préserve 70% d\'eau à la fabrication.',
            'ad_link': 'https://www.amazon.fr/s?k=papier+toilette+recycle'
        },
        {
            'name': 'Relever la cuvette',
            'image': 'wc/relever la cuvette.Webp',
            'description': '🎯 Relève la lunette des toilettes… Bien viser ; essaye un peu pour voir ! 😉',
            'points': 1,
            'fun_text': '🚽 Un petit geste, un grand respect !',
            'ad_text': 'Astuce : un abattant WC à fermeture ralentie évite les claquements !',
            'ad_link': 'https://www.amazon.fr/s?k=abattant+wc+fermeture+ralentie'
        },
        {
            'name': 'Séjourner aux toilettes',
            'image': 'wc/séjourner aux toilettes.webp',
            'description': '📱 Eh oui, c\'est tentant de passer sa vie aux toilettes pour échapper aux corvées ! 😂',
            'points': -3,
            'fun_text': '📱 La bibliothèque préférée de la maison !',
            'ad_text': 'Un repose-pieds physiologique améliore le confort et la santé intestinale !',
            'ad_link': 'https://www.amazon.fr/s?k=repose+pieds+toilettes'
        }
    ],
    'chambre': [
        {
            'name': 'Faire son lit',
            'image': 'chambre ados/faire son lit.webp',
            'description': 'Fait un lit propre et bien rangé !',
            'points': 3,
            'fun_text': '🛏️ Un lit fait = une journée bien commencée !',
            'ad_text': 'Astuce hôtel : tire d\'abord le drap du dessous bien tendu, puis borde les côtés. Résultat pro en 2 min !',
            'ad_link': 'https://www.amazon.fr/s?k=draps+de+lit'
        },
        {
            'name': 'Ranger sa chambre',
            'image': 'chambre ados/ranger sa chambre.webp',
            'description': 'Une chambre bien rangée pour mieux dormir !',
            'points': 5,
            'fun_text': '✨ Une chambre rangée, c\'est un esprit apaisé !',
            'ad_text': 'La règle des 3 piles : à garder, à donner, à laver. En 10 min, ta chambre respire !',
            'ad_link': 'https://www.amazon.fr/s?k=organisateur+placard'
        },
        {
            'name': 'Aérer sa chambre',
            'image': 'chambre ados/aérer sa chambre.webp',
            'description': 'Ouvre la fenêtre pour renouveler l\'air !',
            'points': 2,
            'fun_text': '💨 Un peu d\'air frais, ça fait du bien !',
            'ad_text': 'Aérer 10 minutes par jour réduit l\'humidité et améliore la qualité de ton sommeil !',
            'ad_link': 'https://www.amazon.fr/s?k=purificateur+air'
        },
        {
            'name': 'Mettre ses vêtements dans la corbeille',
            'image': 'chambre ados/mettre ses vetements dans le panier à linge.webp',
            'description': 'Ne laisse pas traîner tes vêtements sales !',
            'points': 2,
            'fun_text': '👕 Direction le panier à linge !',
            'ad_text': 'Un panier à linge bien placé = moins de vêtements par terre !',
            'ad_link': 'https://www.amazon.fr/s?k=panier+linge'
        },
        {
            'name': 'Vider sa corbeille',
            'image': 'chambre ados/vider sa corbeille à papier.webp',
            'description': 'Vide ta poubelle pour garder une chambre propre !',
            'points': 2,
            'fun_text': '🗑️ Hop, à la poubelle !',
            'ad_text': 'Une poubelle vide tous les 2-3 jours évite les mauvaises odeurs !',
            'ad_link': 'https://www.amazon.fr/s?k=poubelle+chambre'
        },
        {
            'name': 'Faire ses devoirs',
            'image': 'chambre ados/Faire ses devoirs.webp',
            'description': 'Travaille sérieusement pour réussir !',
            'points': 8,
            'fun_text': '📚 Le savoir, c\'est le pouvoir !',
            'ad_text': 'La technique Pomodoro : 25 min de travail, 5 min de pause. Efficacité maximale !',
            'ad_link': 'https://www.amazon.fr/s?k=fournitures+scolaires'
        }
    ],
    'chambre_ado': [
        {
            'name': 'Ranger sa chambre',
            'image': 'chambre ados/Ranger sa chambre.webp',
            'description': 'Une chambre bien rangée pour mieux dormir !',
            'points': 5,
            'fun_text': '✨ Une chambre rangée, c\'est un esprit apaisé !',
            'ad_text': 'La règle des 3 piles : à garder, à donner, à laver. En 10 min, ta chambre respire !',
            'ad_link': 'https://www.amazon.fr/s?k=organisateur+placard'
        },
        {
            'name': 'Faire son lit',
            'image': 'chambre ados/faire son lit.webp',
            'description': 'Fait un lit propre et bien rangé !',
            'points': 3,
            'fun_text': '🛏️ Un lit fait = une journée bien commencée !',
            'ad_text': 'Astuce hôtel : tire d\'abord le drap du dessous bien tendu, puis borde les côtés. Résultat pro en 2 min !',
            'ad_link': 'https://www.amazon.fr/s?k=draps+de+lit'
        },
        {
            'name': 'Aérer sa chambre',
            'image': 'chambre ados/aérer sa chambre.webp',
            'description': 'Ouvre la fenêtre pour renouveler l\'air !',
            'points': 2,
            'fun_text': '💨 Un peu d\'air frais, ça fait du bien !',
            'ad_text': 'Aérer 10 minutes par jour réduit l\'humidité et améliore la qualité de ton sommeil !',
            'ad_link': 'https://www.amazon.fr/s?k=purificateur+air'
        },
        {
            'name': 'Mettre ses vêtements dans la corbeille',
            'image': 'chambre ados/mettre ses vetements dans le panier à linge.webp',
            'description': 'Ne laisse pas traîner tes vêtements sales !',
            'points': 2,
            'fun_text': '👕 Direction le panier à linge !',
            'ad_text': 'Un panier à linge bien placé = moins de vêtements par terre !',
            'ad_link': 'https://www.amazon.fr/s?k=panier+linge'
        },
        {
            'name': 'Vider sa corbeille',
            'image': 'chambre ados/vider sa corbeille à papier.webp',
            'description': 'Vide ta poubelle pour garder une chambre propre !',
            'points': 2,
            'fun_text': '🗑️ Hop, à la poubelle !',
            'ad_text': 'Une poubelle vide tous les 2-3 jours évite les mauvaises odeurs !',
            'ad_link': 'https://www.amazon.fr/s?k=poubelle+chambre'
        },
        {
            'name': 'Faire ses devoirs',
            'image': 'chambre ados/Faire ses devoirs.webp',
            'description': 'Travaille sérieusement pour réussir !',
            'points': 8,
            'fun_text': '📚 Le savoir, c\'est le pouvoir !',
            'ad_text': 'La technique Pomodoro : 25 min de travail, 5 min de pause. Efficacité maximale !',
            'ad_link': 'https://www.amazon.fr/s?k=fournitures+scolaires'
        }
    ],
    'salon': [
        {
            'name': 'Ranger le désordre',
            'image': 'salon/Ranger le desordre du salon.webp',
            'description': 'Ranger les objets qui traînent dans le salon',
            'points': 4,
            'fun_text': '🧹 Un salon rangé, c\'est un salon où on respire !',
            'ad_text': 'Paniers et boîtes de rangement !',
            'ad_link': 'https://www.amazon.fr/s?k=rangement+salon'
        },
        {
            'name': 'Faire la poussière',
            'image': 'salon/faire la poussière.webp',
            'description': 'Enlever la poussière sur les meubles',
            'points': 3,
            'fun_text': '✨ Adieu la poussière, bonjour la propreté !',
            'ad_text': 'Chiffons microfibres magiques !',
            'ad_link': 'https://www.amazon.fr/s?k=chiffon+microfibre'
        },
        {
            'name': 'Laver les sols',
            'image': 'salon/laver les sols.webp',
            'description': 'Nettoyer les sols du salon',
            'points': 5,
            'fun_text': '🧼 Des sols qui brillent de mille feux !',
            'ad_text': 'Serpillières et produits sols !',
            'ad_link': 'https://www.amazon.fr/s?k=nettoyage+sol'
        },
        {
            'name': 'Passer l\'aspirateur',
            'image': 'salon/Passer l\'aspirateur.webp',
            'description': 'Aspirer le salon pour un sol propre',
            'points': 5,
            'fun_text': '🌪️ La tornade du ménage passe par ici !',
            'ad_text': 'Aspirateurs performants en promo !',
            'ad_link': 'https://www.amazon.fr/s?k=aspirateur'
        },
        {
            'name': 'Laver les vitres',
            'image': 'salon/laver les vitres.webp',
            'description': 'Nettoyer les vitres du salon',
            'points': 5,
            'fun_text': '🪟 La vue sera encore plus belle !',
            'ad_text': 'Produits vitres sans traces !',
            'ad_link': 'https://www.amazon.fr/s?k=produit+vitres'
        },
        {
            'name': 'Arroser les plantes',
            'image': 'salon/arroser les plantes.webp',
            'description': 'Prendre soin des plantes du salon',
            'points': 2,
            'fun_text': '🌱 Un peu d\'eau pour la jungle urbaine !',
            'ad_text': 'Arrosoirs design et pratiques !',
            'ad_link': 'https://www.amazon.fr/s?k=arrosoir'
        }
    ],
    'chambre_parentale': [
        {
            'name': 'Faire son lit au carré',
            'image': 'chambre parent/faire le lit.webp',
            'description': 'Un lit impeccable comme à l\'armée',
            'points': 3,
            'fun_text': '🛏️ Un lit au carré pour bien démarrer la journée !',
            'ad_text': 'Linge de lit de qualité !',
            'ad_link': 'https://www.amazon.fr/s?k=draps+de+lit'
        },
        {
            'name': 'Changer les draps',
            'image': 'chambre parent/changer les draps du lit.webp',
            'description': 'Renouveler le linge de lit',
            'points': 4,
            'fun_text': '🧺 Des draps frais pour de beaux rêves !',
            'ad_text': 'Draps confortables en promo !',
            'ad_link': 'https://www.amazon.fr/s?k=draps'
        },
        {
            'name': 'Ranger ses vêtements',
            'image': 'chambre parent/ranger ses vetements.webp',
            'description': 'Ranger les vêtements dans l\'armoire',
            'points': 3,
            'fun_text': '👔 Une armoire bien organisée !',
            'ad_text': 'Organisateurs de placard !',
            'ad_link': 'https://www.amazon.fr/s?k=organisateur+placard'
        }
    ],
    'salle_bain': [
        {
            'name': 'Se laver les dents',
            'image': 'salle de bain/se laver es dents.webp',
            'description': 'Un sourire éclatant',
            'points': 1,
            'fun_text': '🦷 Un sourire éclatant pour bien commencer la journée !',
            'ad_text': 'Brosses à dents électriques !',
            'ad_link': 'https://www.amazon.fr/s?k=brosse+dents+electrique'
        },
        {
            'name': 'Reboucher le dentifrice',
            'image': 'salle de bain/reboucher le dentifrice.webp',
            'description': 'Le dentifrice bien fermé',
            'points': 1,
            'fun_text': '🧴 Un tube bien fermé pour éviter le gaspillage !',
            'ad_text': 'Dentifrices pour toute la famille !',
            'ad_link': 'https://www.amazon.fr/s?k=dentifrice'
        },
        {
            'name': 'Nettoyer ses cheveux',
            'image': 'salle de bain/nettoyer les cheveux.webp',
            'description': 'Enlever les cheveux du lavabo',
            'points': 2,
            'fun_text': '💇 Plus de cheveux dans le lavabo !',
            'ad_text': 'Accessoires salle de bain !',
            'ad_link': 'https://www.amazon.fr/s?k=accessoires+salle+de+bain'
        },
        {
            'name': 'Nettoyer ses poils de barbe',
            'image': 'salle de bain/nettoyer les poils de barbe.webp',
            'description': 'Nettoyer les poils de barbe du lavabo',
            'points': 2,
            'fun_text': '🪒 La barbe de trois jours se range !',
            'ad_text': 'Rasoirs et accessoires !',
            'ad_link': 'https://www.amazon.fr/s?k=rasoir'
        },
        {
            'name': 'Jeter les bouteilles vides',
            'image': 'salle de bain/jeter les bouteilles de savon vide. wepb.webp',
            'description': 'Vider les bouteilles vides',
            'points': 2,
            'fun_text': '♻️ Faire de la place pour les nouvelles !',
            'ad_text': 'Organisateurs salle de bain !',
            'ad_link': 'https://www.amazon.fr/s?k=rangement+salle+de+bain'
        },
        {
            'name': 'Éponger l\'eau par terre',
            'image': 'salle de bain/éponger le sol.webp',
            'description': 'Sécher l\'eau au sol',
            'points': 3,
            'fun_text': '💦 Plus de flaques pour éviter de glisser !',
            'ad_text': 'Tapis de bain absorbants !',
            'ad_link': 'https://www.amazon.fr/s?k=tapis+bain'
        }
    ],
    'garage': [
        {
            'name': 'Ranger les outils',
            'image': 'salon/Passer l\'aspirateur.webp',
            'description': 'Un garage bien organisé !',
            'points': 5,
            'ad_text': 'Solutions de rangement garage !',
            'ad_link': 'https://www.amazon.fr/s?k=rangement+garage'
        },
        {
            'name': 'Balayer le garage',
            'image': 'salon/Passer l\'aspirateur.webp',
            'description': 'Un garage propre !',
            'points': 4,
            'ad_text': 'Matériel de nettoyage !',
            'ad_link': 'https://www.amazon.fr/s?k=balai+garage'
        }
    ],
    'piece_bonus': [
        {
            'name': 'Penser au goûter',
            'image': 'bonus/penser au gouter.webp',
            'description': 'Préparer le goûter des enfants',
            'points': 2,
            'fun_text': '🍪 Le goûter c\'est important !',
            'ad_text': 'Boîtes à goûter !',
            'ad_link': 'https://www.amazon.fr/s?k=boite+gouter'
        },
        {
            'name': 'Signer les mots',
            'image': 'bonus/signer les mots.webp',
            'description': 'Signer les mots de l\'école',
            'points': 2,
            'fun_text': '✍️ Les devoirs administratifs !',
            'ad_text': 'Fournitures scolaires !',
            'ad_link': 'https://www.amazon.fr/s?k=fournitures+scolaires'
        },
        {
            'name': 'Aller aux réunions d\'école',
            'image': 'bonus/aller aux reunions d\'ecole.webp',
            'description': 'Participer aux réunions scolaires',
            'points': 5,
            'fun_text': '🏫 Le suivi scolaire c\'est essentiel !',
            'ad_text': 'Agendas pour parents !',
            'ad_link': 'https://www.amazon.fr/s?k=agenda+parents'
        },
        {
            'name': 'Prendre les RDV médicaux',
            'image': 'bonus/prendre les rdv médicaux.webp',
            'description': 'Gérer les rendez-vous médicaux',
            'points': 3,
            'fun_text': '🏥 La santé avant tout !',
            'ad_text': 'Applications de santé !',
            'ad_link': 'https://www.amazon.fr/s?k=carnet+santé'
        },
        {
            'name': 'Organiser les anniversaires',
            'image': 'bonus/organiser les anniversaire.webp',
            'description': 'Préparer les fêtes d\'anniversaire',
            'points': 5,
            'fun_text': '🎉 Les anniversaires c\'est la fête !',
            'ad_text': 'Décorations d\'anniversaire !',
            'ad_link': 'https://www.amazon.fr/s?k=decoration+anniversaire'
        },
        {
            'name': 'Déclarer les impôts',
            'image': 'bonus/déclarer les impôts.webp',
            'description': 'Gérer les déclarations fiscales',
            'points': 6,
            'fun_text': '💰 Les devoirs citoyens !',
            'ad_text': 'Solutions de gestion administrative !',
            'ad_link': 'https://www.amazon.fr/s?k=classeur+documents'
        }
    ],
    'chambre_garcon': [
        {
            'name': 'Faire son lit',
            'image': 'chambre ados/faire son lit.webp',
            'description': 'Bien faire son lit le matin',
            'points': 3,
            'fun_text': '🛏️ Un lit bien fait, une journée bien partie !',
            'ad_text': 'Parures de lit pour chambre enfant !',
            'ad_link': 'https://www.amazon.fr/s?k=parure+lit+enfant'
        },
        {
            'name': 'Ranger sa chambre',
            'image': 'chambre ados/Ranger sa chambre.webp',
            'description': 'Remettre de l\'ordre dans la chambre',
            'points': 4,
            'fun_text': '✨ Une chambre rangée c\'est une chambre heureuse !',
            'ad_text': 'Rangements pratiques pour chambre enfant !',
            'ad_link': 'https://www.amazon.fr/s?k=rangement+chambre+enfant'
        },
        {
            'name': 'Aérer sa chambre',
            'image': 'chambre ados/aérer sa chambre.webp',
            'description': 'Ouvrir la fenêtre pour renouveler l\'air',
            'points': 2,
            'fun_text': '💨 Un air frais pour bien dormir !',
            'ad_text': 'Purificateurs d\'air pour chambre !',
            'ad_link': 'https://www.amazon.fr/s?k=purificateur+air+chambre'
        },
        {
            'name': 'Mettre les vêtements dans le panier',
            'image': 'chambre ados/mettre ses vetements dans le panier à linge.webp',
            'description': 'Trier les vêtements sales',
            'points': 3,
            'fun_text': '👕 Droit au but, dans le panier !',
            'ad_text': 'Paniers à linge design !',
            'ad_link': 'https://www.amazon.fr/s?k=panier+linge+enfant'
        },
        {
            'name': 'Vider sa corbeille',
            'image': 'chambre ados/vider sa corbeille à papier.webp',
            'description': 'Vider la corbeille à papier',
            'points': 2,
            'fun_text': '🗑️ Poubelle vide, esprit clair !',
            'ad_text': 'Jolies corbeilles pour chambre !',
            'ad_link': 'https://www.amazon.fr/s?k=corbeille+chambre+enfant'
        },
        {
            'name': 'Faire ses devoirs',
            'image': 'chambre ados/Faire ses devoirs.webp',
            'description': 'Faire les devoirs du soir',
            'points': 5,
            'fun_text': '📚 Les devoirs d\'abord, les jeux ensuite !',
            'ad_text': 'Fournitures scolaires et bureaux enfants !',
            'ad_link': 'https://www.amazon.fr/s?k=bureau+enfant+scolaire'
        }
    ],
    'chambre_enfant': [
        {
            'name': 'Ranger ses jouets',
            'image': 'chambre enfant/ranger ses jouets.webp',
            'description': 'Remettre de l\'ordre dans la chambre',
            'points': 4,
            'fun_text': '🧸 Une chambre bien rangée pour mieux jouer !',
            'ad_text': 'Boîtes de rangement pour enfants !',
            'ad_link': 'https://www.amazon.fr/s?k=rangement+enfant'
        },
        {
            'name': 'Lire 10 minutes par jour',
            'image': 'chambre enfant/lire dix minutes par jour.webp',
            'description': 'Un moment de lecture quotidien',
            'points': 3,
            'fun_text': '📚 Lire c\'est grandir !',
            'ad_text': 'Livres pour enfants !',
            'ad_link': 'https://www.amazon.fr/s?k=livres+enfant'
        }
    ],
    'chambre_bebe': [
        {
            'name': 'Donner le biberon',
            'image': 'chambre bébé/donner le biberon.webp',
            'description': 'Nourrir bébé avec amour !',
            'points': 5,
            'fun_text': '🍼 L\'heure du biberon !',
            'ad_text': 'Les meilleurs biberons anti-coliques pour bébé !',
            'ad_link': 'https://www.amazon.fr/s?k=biberon+bebe'
        },
        {
            'name': 'Changer les couches',
            'image': 'chambre bébé/changer les couches.webp',
            'description': 'Un bébé propre et confortable !',
            'points': 4,
            'fun_text': '👶 Change moi vite !',
            'ad_text': 'Couches douces et absorbantes pour bébé !',
            'ad_link': 'https://www.amazon.fr/s?k=couches+bebe'
        },
        {
            'name': 'Faire dormir le bébé',
            'image': 'chambre bébé/endormir le bébé.webp',
            'description': 'Un dodo paisible pour bébé !',
            'points': 6,
            'fun_text': '😴 Dodo, l\'enfant do !',
            'ad_text': 'Veilleuses et musiques douces pour endormir bébé !',
            'ad_link': 'https://www.amazon.fr/s?k=veilleuse+bebe'
        },
        {
            'name': 'Laver les vêtements',
            'image': 'chambre bébé/laver les vêtements.webp',
            'description': 'Des petits habits tout propres !',
            'points': 4,
            'fun_text': '👕 Lessive spéciale bébé !',
            'ad_text': 'Lessives hypoallergéniques pour la peau de bébé !',
            'ad_link': 'https://www.amazon.fr/s?k=lessive+bebe'
        },
        {
            'name': 'Vider la poubelle',
            'image': 'chambre bébé/vider la poubelle.webp',
            'description': 'Vider la poubelle à couches !',
            'points': 3,
            'fun_text': '🗑️ Une chambre sans odeurs !',
            'ad_text': 'Poubelles à couches anti-odeurs !',
            'ad_link': 'https://www.amazon.fr/s?k=poubelle+couches'
        }
    ],
    'wc': [
        {
            'name': 'Nettoyer les toilettes',
            'image': 'wc/laver_toillettes.webp',
            'description': '🚽 Nettoyer des toilettes ça vaut des points, personne n\'aime laver les chiottes… 😉 !',
            'points': 6,
            'fun_text': '🚽 Le trône mérite un peu d\'attention royale !',
            'ad_text': 'Verse un verre de coca dans la cuvette, laisse agir 1h : détartrage express et naturel !',
            'ad_link': 'https://www.amazon.fr/s?k=produits+toilettes'
        },
        {
            'name': 'Changer le rouleau de papier toilette',
            'image': 'wc/jeter_rouleaux.png',
            'description': '🧻 Tu peux jeter les rouleaux ou en faire des ronds de serviettes ! 😄',
            'points': 2,
            'fun_text': '🧻 Le héros silencieux de la maison !',
            'ad_text': 'Le saviez-vous ? Le papier recyclé est tout aussi doux et préserve 70% d\'eau à la fabrication.',
            'ad_link': 'https://www.amazon.fr/s?k=papier+toilette+recycle'
        },
        {
            'name': 'Relever la cuvette',
            'image': 'wc/relever la cuvette.Webp',
            'description': '🎯 Relève la lunette des toilettes… Bien viser ; essaye un peu pour voir ! 😉',
            'points': 1,
            'fun_text': '🚽 Un petit geste, un grand respect !',
            'ad_text': 'Astuce : un abattant WC à fermeture ralentie évite les claquements !',
            'ad_link': 'https://www.amazon.fr/s?k=abattant+wc+fermeture+ralentie'
        },
        {
            'name': 'Séjourner aux toilettes',
            'image': 'wc/séjourner aux toilettes.webp',
            'description': '📱 Eh oui, c\'est tentant de passer sa vie aux toilettes pour échapper aux corvées ! 😂',
            'points': -3,
            'fun_text': '📱 La bibliothèque préférée de la maison !',
            'ad_text': 'Un repose-pieds physiologique améliore le confort et la santé intestinale !',
            'ad_link': 'https://www.amazon.fr/s?k=repose+pieds+toilettes'
        }
    ],
    'garage': [
        {
            'name': 'Laver la voiture',
            'image': 'garage/carwash.webp',
            'description': 'Une voiture propre et brillante !',
            'points': 5,
            'fun_text': '🚗 Ça brille de mille feux !',
            'ad_text': 'Produits pour un lavage auto impeccable !',
            'ad_link': 'https://www.amazon.fr/s?k=lavage+voiture'
        },
        {
            'name': 'Prendre de l\'essence',
            'image': 'garage/Prendre de l\'essence.webp',
            'description': 'Faire le plein de carburant',
            'points': 3,
            'fun_text': '⛽ Le plein d\'énergie !',
            'ad_text': 'Carte carburant pour économiser !',
            'ad_link': 'https://www.amazon.fr/s?k=carte+carburant'
        },
        {
            'name': 'Contrôle technique',
            'image': 'garage/contrôle technique .webp',
            'description': 'Passer le contrôle technique du véhicule',
            'points': 6,
            'fun_text': '🔧 Sécurité avant tout !',
            'ad_text': 'Kit d\'entretien auto !',
            'ad_link': 'https://www.amazon.fr/s?k=entretien+voiture'
        }
    ]
}

# ===============================
# FONCTION DE NORMALISATION DES CATÉGORIES
# ===============================

def normalize_category(cat):
    """Convertit les noms de catégories avec majuscules/accents vers les clés TASKS_CONFIG"""
    # Dictionnaire de correspondance entre noms affichés et clés TASKS_CONFIG
    category_map = {
        'Salon': 'salon',
        'Cuisine': 'cuisine',
        'Chambre Ado': 'chambre_ado',
        'Bureau': 'piece_bonus',
        'Chambre Parentale': 'chambre_parentale',
        'Salle Bain': 'salle_bain',
        'Chambre Enfant': 'chambre_enfant',
        'Chambre Bébé': 'chambre_bebe',
        'WC': 'wc',
        'Garage': 'garage',
        'Buanderie': 'buanderie',
        # Variantes minuscules pour compatibilité
        'salon': 'salon',
        'cuisine': 'cuisine',
        'chambre ado': 'chambre_ado',
        'chambre_ado': 'chambre_ado',
        'piece bonus': 'piece_bonus',
        'pièce bonus': 'piece_bonus',
        'piece_bonus': 'piece_bonus',
        'bureau': 'piece_bonus',
        'chambre parentale': 'chambre_parentale',
        'chambre_parentale': 'chambre_parentale',
        'salle bain': 'salle_bain',
        'salle_bain': 'salle_bain',
        'chambre enfant': 'chambre_enfant',
        'chambre_enfant': 'chambre_enfant',
        'chambre garcon': 'chambre_garcon',
        'chambre_garcon': 'chambre_garcon',
        'chambre bebe': 'chambre_bebe',
        'chambre_bebe': 'chambre_bebe',
        'wc': 'wc',
        'garage': 'garage',
        'buanderie': 'buanderie',
    }
    return category_map.get(cat, cat.lower().replace(' ', '_'))


# ===============================
# CONFIGURATION EMAIL
# ===============================

def get_completed_tasks(user_email, category):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT task_name FROM completed_tasks WHERE user_email=? AND category=?",
              (user_email, category))
    tasks = [row[0] for row in c.fetchall()]
    conn.close()
    return tasks



def generate_house_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ===== PALETTE DE COULEURS POUR LES JOUEURS =====
PLAYER_COLOR_PALETTE = [
    '#FF4D6D',  # Rouge framboise
    '#00B4D8',  # Bleu azur
    '#06D6A0',  # Vert menthe vif
    '#FFB703',  # Jaune soleil
    '#8B5CF6',  # Violet électrique
    '#F77F00',  # Orange vif
    '#3A86FF',  # Bleu roi
    '#FF006E',  # Rose choc
    '#2DC653',  # Vert lime
    '#FB5607',  # Orange brûlé
    '#9B5DE5',  # Violet lilas
    '#00F5D4',  # Turquoise néon
]


def assign_player_color(email, house_id=None):
    """
    Attribue une couleur unique à un joueur dans sa maison.
    Si house_id est fourni, s'assure que la couleur est unique dans la maison.
    Sinon, assigne une couleur aléatoire.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        if house_id:
            # Récupérer les couleurs déjà utilisées dans cette maison
            c.execute("""
                SELECT player_color FROM users 
                WHERE house_id = ? AND player_color IS NOT NULL
            """, (house_id,))
            used_colors = [row[0] for row in c.fetchall()]
            
            # Trouver une couleur disponible
            import random
            available_colors = [c for c in PLAYER_COLOR_PALETTE if c not in used_colors]
            if not available_colors:
                # Si toutes les couleurs sont utilisées, recommencer avec toute la palette
                available_colors = PLAYER_COLOR_PALETTE
            color = random.choice(available_colors)
        else:
            # Couleur aléatoire si pas de maison
            color = random.choice(PLAYER_COLOR_PALETTE)
        
        # Attribuer la couleur au joueur
        c.execute("UPDATE users SET player_color = ? WHERE email = ?", (color, email))
        conn.commit()
        return color
        
    finally:
        conn.close()


def get_player_color(email):
    """
    Récupère la couleur d'un joueur. Si aucune couleur n'est définie,
    en assigne une automatiquement.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("SELECT player_color, house_id FROM users WHERE email = ?", (email,))
        result = c.fetchone()
        
        if not result:
            return PLAYER_COLOR_PALETTE[0]  # Couleur par défaut
        
        color, house_id = result
        
        if not color:
            # Assigner une couleur si le joueur n'en a pas
            color = assign_player_color(email, house_id)
        
        return color
        
    finally:
        conn.close()


def get_house_players_with_colors(house_id):
    """
    Récupère tous les joueurs d'une maison avec leurs couleurs.
    Retourne une liste de dictionnaires avec les infos des joueurs.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT email, name, avatar, avatar_file, avatar_url, points, player_color
            FROM users
            WHERE house_id = ?
            ORDER BY points DESC
        """, (house_id,))
        
        players = []
        for row in c.fetchall():
            email, name, avatar, avatar_file, avatar_url, points, color = row
            
            # Assigner une couleur si nécessaire
            if not color:
                color = assign_player_color(email, house_id)
            
            players.append({
                'email': email,
                'name': name or email.split('@')[0],
                'avatar': avatar,
                'avatar_file': validate_avatar_file(avatar_file),
                'avatar_url': avatar_url,
                'points': points or 0,
                'color': color
            })
        
        return players
        
    finally:
        conn.close()


def get_player_colors_map(player_emails):
    """Génère une couleur unique pour chaque joueur basée sur l'ordre alphabétique des emails"""
    # Palette de 10 couleurs pastel douces et harmonieuses inspirées de task_enhanced
    colors = [
        'linear-gradient(135deg, rgba(120, 180, 230, 0.75) 0%, rgba(100, 160, 210, 0.65) 100%)',  # Bleu pastel
        'linear-gradient(135deg, rgba(180, 140, 200, 0.75) 0%, rgba(160, 120, 180, 0.65) 100%)',  # Violet pastel
        'linear-gradient(135deg, rgba(240, 140, 140, 0.75) 0%, rgba(220, 120, 120, 0.65) 100%)',  # Rose pastel
        'linear-gradient(135deg, rgba(250, 180, 100, 0.75) 0%, rgba(230, 160, 80, 0.65) 100%)',   # Pêche pastel
        'linear-gradient(135deg, rgba(130, 200, 150, 0.75) 0%, rgba(110, 180, 130, 0.65) 100%)',  # Vert pastel
        'linear-gradient(135deg, rgba(240, 150, 170, 0.75) 0%, rgba(220, 130, 150, 0.65) 100%)',  # Rose fuchsia pastel
        'linear-gradient(135deg, rgba(120, 210, 200, 0.75) 0%, rgba(100, 190, 180, 0.65) 100%)',  # Turquoise pastel
        'linear-gradient(135deg, rgba(255, 170, 170, 0.75) 0%, rgba(240, 150, 150, 0.65) 100%)',  # Corail pastel
        'linear-gradient(135deg, rgba(140, 220, 210, 0.75) 0%, rgba(120, 200, 190, 0.65) 100%)',  # Menthe pastel
        'linear-gradient(135deg, rgba(255, 200, 120, 0.75) 0%, rgba(240, 180, 100, 0.65) 100%)',  # Ambre pastel
    ]
    
    # Trier les emails pour avoir un ordre cohérent
    sorted_emails = sorted(player_emails)
    
    # Créer un dictionnaire email -> couleur
    color_map = {}
    for i, email in enumerate(sorted_emails):
        color_index = i % len(colors)
        color_map[email] = {
            'vertical': colors[color_index],
            'horizontal': colors[color_index].replace('135deg', '90deg')
        }
    
    return color_map


# ===============================
# BASE DE DONNÉES
# ===============================
def init_db():
    import sys
    print('init_db START', flush=True)
    conn = get_db_connection()
    # ⚠️ IMPORTANT PostgreSQL: autocommit=True pour que chaque DDL soit sa propre transaction.
    # Avec autocommit=False (défaut), si une instruction échoue et déclenche un ROLLBACK,
    # TOUTES les tables créées dans la même transaction sont annulées.
    # autocommit=True évite ce problème : chaque CREATE TABLE/INDEX est atomique.
    if _USE_PG and hasattr(conn._conn, 'autocommit'):
        conn._conn.autocommit = True
    print('init_db DB connected', flush=True)
    c = conn.cursor()
    c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    points INTEGER DEFAULT 0,
    house_id INTEGER,
    avatar TEXT DEFAULT 'lorelei-default',
    name TEXT,
    photo_filename TEXT,
    avatar_url TEXT
)
""")

    # Ajouter les nouvelles colonnes users si elles n'existent pas
    # (les ALTER TABLE sont traduits en ADD COLUMN IF NOT EXISTS pour PostgreSQL via _adapt())
    try:
        c.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except Exception:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN photo_filename TEXT")
    except Exception:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
    except Exception:
        pass

    # Colonnes pour les comptes enfants
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_child_account INTEGER DEFAULT 0")
    except Exception:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN created_by TEXT")
    except Exception:
        pass
    
    # Colonne pour la couleur personnelle du joueur
    try:
        c.execute("ALTER TABLE users ADD COLUMN player_color TEXT")
    except Exception:
        pass
    
    # Colonnes pour le système d'avatars DiceBear
    try:
        c.execute("ALTER TABLE users ADD COLUMN avatar_style TEXT DEFAULT 'lorelei'")
    except Exception:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN avatar_file TEXT")
    except Exception:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN registration_step TEXT")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN firstname TEXT")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN skull_count INTEGER DEFAULT 0")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN skull_expires_at TEXT")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN bonus_expires_at TEXT")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN has_seen_onboarding INTEGER DEFAULT 0")
    except Exception:
        pass

    # Thème de fond par joueur (indépendant de la maison)
    try:
        c.execute("ALTER TABLE users ADD COLUMN bg_theme TEXT DEFAULT 'marron'")
        conn.commit()
    except Exception:
        pass  # Colonne déjà existante

# Table houses
    c.execute("""
        CREATE TABLE IF NOT EXISTS houses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        code TEXT UNIQUE,
        house_name TEXT,
        progress INTEGER DEFAULT 0
        )
        """)
    
    # Ajouter les nouvelles colonnes houses si elles n'existent pas
    try:
        c.execute("ALTER TABLE houses ADD COLUMN house_name TEXT")
    except Exception:
        pass
    
    try:
        c.execute("ALTER TABLE houses ADD COLUMN progress INTEGER DEFAULT 0")
    except Exception:
        pass
    
    try:
        c.execute("ALTER TABLE houses ADD COLUMN house_type TEXT DEFAULT 'family'")
    except Exception:
        pass

    # Migration: thème de fond
    try:
        c.execute("ALTER TABLE houses ADD COLUMN bg_theme TEXT DEFAULT 'marron'")
        conn.commit()
    except Exception:
        pass  # Colonne déjà existante

    # Colonnes ajoutées dans des versions ultérieures
    try:
        c.execute("ALTER TABLE houses ADD COLUMN health INTEGER DEFAULT 100")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE houses ADD COLUMN level INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE houses ADD COLUMN mood TEXT DEFAULT 'happy'")
    except Exception:
        pass
    # Réinitialisation quotidienne: stocker la dernière date de reset
    try:
        c.execute("ALTER TABLE houses ADD COLUMN last_reset_date TEXT")
    except Exception:
        pass
    
    # Réinitialisation hebdomadaire: stocker la dernière date de reset hebdomadaire  
    try:
        c.execute("ALTER TABLE houses ADD COLUMN last_weekly_reset_date TEXT")
    except Exception:
        pass
    
    # Type de foyer pour les récompenses (family, couple, coloc)
    try:
        c.execute("ALTER TABLE houses ADD COLUMN house_type TEXT DEFAULT 'family'")
    except Exception:
        pass

    # Table pour les tâches personnalisées
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_id INTEGER,
        task_name TEXT,
        task_description TEXT,
        category TEXT,
        task_image TEXT,
        points INTEGER,
        ad_text TEXT,
        ad_link TEXT,
        created_by TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(house_id) REFERENCES houses(id)
        )
        """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        cost INTEGER
    )
    """)

    # Table user_rewards (récompenses possédées par chaque utilisateur)
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        reward_id INTEGER,
        purchased_date DATE DEFAULT CURRENT_DATE,
        FOREIGN KEY(user_email) REFERENCES users(email),
        FOREIGN KEY(reward_id) REFERENCES rewards(id)
    )
    """)
    
    # Ajouter la colonne purchased_date si elle n'existe pas (pour les bases existantes)
    try:
        c.execute("ALTER TABLE user_rewards ADD COLUMN purchased_date DATE DEFAULT CURRENT_DATE")
    except Exception:
        pass  # La colonne existe déjà
    c.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_email) REFERENCES users(email)
    )
    """)
    
    # Table messages améliorée avec système de notification et messages automatiques
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_id INTEGER NOT NULL,
        sender_email TEXT,
        sender_type TEXT DEFAULT 'user',
        content TEXT NOT NULL,
        message_type TEXT DEFAULT 'chat',
        related_task_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(house_id) REFERENCES houses(id),
        FOREIGN KEY(sender_email) REFERENCES users(email)
    )
    """)
    
    # Table pour tracker les messages lus par utilisateur
    c.execute("""
    CREATE TABLE IF NOT EXISTS message_reads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        user_email TEXT NOT NULL,
        read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(message_id) REFERENCES messages(id),
        FOREIGN KEY(user_email) REFERENCES users(email),
        UNIQUE(message_id, user_email)
    )
    """)
    
    # Ajouter la colonne recipient_email pour les messages privés
    try:
        c.execute("ALTER TABLE messages ADD COLUMN recipient_email TEXT")
    except Exception:
        pass  # La colonne existe déjà

    # Catégorie liée pour les messages task_added (pastille sur pièce du menu)
    try:
        c.execute("ALTER TABLE messages ADD COLUMN related_category TEXT")
    except Exception:
        pass  # La colonne existe déjà
    
    # 🔔 Table pour les subscriptions push notifications
    c.execute("""
    CREATE TABLE IF NOT EXISTS push_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        p256dh_key TEXT NOT NULL,
        auth_key TEXT NOT NULL,
        user_agent TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(user_email) REFERENCES users(email),
        UNIQUE(user_email, endpoint)
    )
    """)

    # Overrides des points par maison et par tâche prédéfinie (indexée)
    c.execute("""
        CREATE TABLE IF NOT EXISTS task_points_overrides (
            house_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            task_index INTEGER NOT NULL,
            points INTEGER NOT NULL,
            PRIMARY KEY (house_id, category, task_index),
            FOREIGN KEY(house_id) REFERENCES houses(id)
        )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS completed_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        house_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        task_name TEXT NOT NULL,
        points INTEGER DEFAULT 0,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
    # Migration: si une ancienne version de la table existe avec d'autres colonnes,
    # ajouter les colonnes manquantes sans perdre les données.
    try:
        c.execute("PRAGMA table_info(completed_tasks)")
        existing_cols = {row[1] for row in c.fetchall()}
        # Colonnes que notre code attend
        needed = {
            'user_email': "TEXT",
            'category': "TEXT",
            'completed_at': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        }
        for col, col_def in needed.items():
            if col not in existing_cols:
                try:
                    c.execute(f"ALTER TABLE completed_tasks ADD COLUMN {col} {col_def}")
                except Exception:
                    pass
    except Exception:
        pass
    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        house_id INTEGER NOT NULL,
        date DATE NOT NULL,
        prize TEXT,
        FOREIGN KEY(user_email) REFERENCES users(email),
        UNIQUE(user_email, date)
    )
    """)

    # Table pour les cadeaux révélés (Dust)
    c.execute("""
    CREATE TABLE IF NOT EXISTS revealed_gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_id INTEGER NOT NULL,
        gift_id INTEGER NOT NULL,
        revealed_by TEXT NOT NULL,
        revealed_date TEXT NOT NULL,
        FOREIGN KEY(house_id) REFERENCES houses(id),
        FOREIGN KEY(revealed_by) REFERENCES users(email),
        UNIQUE(house_id, gift_id)
    )
    """)

    # Table pour les récompenses mystère gagnées par les joueurs
    c.execute("""
    CREATE TABLE IF NOT EXISTS mystery_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        house_id INTEGER NOT NULL,
        reward_text TEXT NOT NULL,
        won_date DATE DEFAULT CURRENT_DATE,
        used INTEGER DEFAULT 0,
        used_date DATE,
        FOREIGN KEY(user_email) REFERENCES users(email),
        FOREIGN KEY(house_id) REFERENCES houses(id)
    )
    """)

    # Table pour le suivi des tâches de bébé (biberon, couches, sommeil)
    c.execute("""
    CREATE TABLE IF NOT EXISTS baby_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        house_id INTEGER NOT NULL,
        task_type TEXT NOT NULL,
        tracking_time TEXT NOT NULL,
        bottle_ml INTEGER,
        observations TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_email) REFERENCES users(email),
        FOREIGN KEY(house_id) REFERENCES houses(id)
    )
    """)

    # Table pour les pièces personnalisées (noms custom + masquées)
    c.execute("""
    CREATE TABLE IF NOT EXISTS custom_rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_id INTEGER NOT NULL,
        room_key TEXT NOT NULL,
        custom_name TEXT,
        custom_image TEXT,
        is_hidden INTEGER DEFAULT 0,
        UNIQUE(house_id, room_key),
        FOREIGN KEY(house_id) REFERENCES houses(id)
    )
    """)

    # Table pour les tokens de réinitialisation de mot de passe
    c.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)

    # Table pour les feedbacks des testeurs bêta
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_reminder_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT UNIQUE NOT NULL,
        reminders_enabled INTEGER DEFAULT 1,
        reminder_frequency TEXT DEFAULT 'daily',
        quiet_hours_start TEXT DEFAULT '22:00',
        quiet_hours_end TEXT DEFAULT '08:00'
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS beta_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_email TEXT,
        user_name TEXT,
        note_globale INTEGER,
        note_facilite INTEGER,
        note_design INTEGER,
        ce_qui_plait TEXT,
        ce_qui_deplait TEXT,
        ameliorations TEXT,
        pret_a_payer INTEGER DEFAULT 0,
        prix_acceptable TEXT,
        recommande INTEGER,
        autres_commentaires TEXT
    )
    """)

    # Table pour les rappels personnels des joueurs (mini agenda / to-do list)
    c.execute("""
    CREATE TABLE IF NOT EXISTS player_reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        house_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        remind_at TEXT,
        is_done INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table demandes de preuve (système de vigilance sociale)
    c.execute("""
    CREATE TABLE IF NOT EXISTS proof_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_id INTEGER NOT NULL,
        requester_email TEXT NOT NULL,
        target_email TEXT NOT NULL,
        task_name TEXT NOT NULL,
        task_points INTEGER DEFAULT 0,
        completed_task_id INTEGER,
        status TEXT DEFAULT 'pending',
        photo_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table des suspicions (système de gameplay avec preuves photo)
    c.execute("""
    CREATE TABLE IF NOT EXISTS suspicions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_id INTEGER NOT NULL,
        suspecting_player_email TEXT NOT NULL,
        suspected_player_email TEXT NOT NULL,
        task_name TEXT NOT NULL,
        task_points INTEGER DEFAULT 0,
        completed_task_id INTEGER,
        status TEXT DEFAULT 'pending',
        photo_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        FOREIGN KEY(house_id) REFERENCES houses(id),
        FOREIGN KEY(suspecting_player_email) REFERENCES users(email),
        FOREIGN KEY(suspected_player_email) REFERENCES users(email)
    )
    """)

    # Table logs de connexion (suivi bêta-testeurs)
    c.execute("""
    CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip TEXT
    )
    """)

    # === INDEX POUR AMÉLIORER LES PERFORMANCES ===
    # Chaque CREATE INDEX est dans try/except : si une table/colonne n'existe pas encore,
    # on logue l'erreur mais on ne crash pas init_db()
    _indexes = [
        "CREATE INDEX IF NOT EXISTS idx_completed_tasks_user ON completed_tasks(user_email)",
        "CREATE INDEX IF NOT EXISTS idx_completed_tasks_house ON completed_tasks(house_id)",
        "CREATE INDEX IF NOT EXISTS idx_completed_tasks_date ON completed_tasks(completed_at)",
        "CREATE INDEX IF NOT EXISTS idx_completed_tasks_user_date ON completed_tasks(user_email, completed_at)",
        "CREATE INDEX IF NOT EXISTS idx_users_house ON users(house_id)",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_houses_code ON houses(code)",
        "CREATE INDEX IF NOT EXISTS idx_messages_house ON messages(house_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(house_id, message_type)",
        "CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_email)",
        "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_email)",
        "CREATE INDEX IF NOT EXISTS idx_message_reads_user ON message_reads(user_email, message_id)",
        "CREATE INDEX IF NOT EXISTS idx_message_reads_msg ON message_reads(message_id)",
        "CREATE INDEX IF NOT EXISTS idx_custom_rooms_house ON custom_rooms(house_id)",
        "CREATE INDEX IF NOT EXISTS idx_player_reminders_user ON player_reminders(user_email)",
    ]
    for _idx_sql in _indexes:
        try:
            c.execute(_idx_sql)
        except Exception as _idx_err:
            print(f'⚠️ init_db index ignoré ({_idx_err})', flush=True)

    # === Migration: Corriger les anciens messages avec nom de maison ou NULL comme sender_email ===
    # Avant une certaine version, task_added/courses_added/baby_tracking stockaient le nom de la maison
    # au lieu de l'email du joueur. On corrige en cherchant le créateur par son nom dans le contenu.
    try:
        c.execute("""
            SELECT id, house_id, content FROM messages
            WHERE message_type IN ('task_added', 'courses_added', 'baby_tracking')
            AND (sender_email IS NULL OR sender_email NOT LIKE '%@%')
        """)
        _old_msgs = c.fetchall()
        for _msg_id, _msg_house_id, _content in _old_msgs:
            if not _msg_house_id or not _content:
                continue
            _m = re.search(r'^\S+ (.+?) a ', _content)
            if not _m:
                continue
            _creator_name = _m.group(1).strip()
            c.execute("SELECT email FROM users WHERE house_id=? AND name=?", (_msg_house_id, _creator_name))
            _user_row = c.fetchone()
            if _user_row:
                c.execute("UPDATE messages SET sender_email=? WHERE id=?", (_user_row[0], _msg_id))
        if _old_msgs:
            print(f'✅ Migration sender_email: {len(_old_msgs)} message(s) corrigé(s)', flush=True)
    except Exception as _mig_emails:
        print(f'⚠️ Migration sender_email messages: {_mig_emails}', flush=True)

    # Sur SQLite : commit final nécessaire. Sur PostgreSQL (autocommit=True) : no-op, chaque statement déjà commité.
    if not _USE_PG:
        conn.commit()
    conn.close()

try:
    init_db()
except Exception as _init_db_err:
    import traceback
    print(f'❌ ERREUR CRITIQUE init_db(): {_init_db_err}', flush=True)
    traceback.print_exc()

# === CONFIGURATION DU CACHE POUR LES FICHIERS STATIQUES ===
@app.after_request
def add_cache_headers(response):
    """Ajouter des headers de cache pour les fichiers statiques"""
    if 'static' in request.path:
        # manifest.json : jamais de cache (doit être contrôlé en priorité avant .js)
        if 'manifest.json' in request.path:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        # Cache les images/avatars/SVG pendant 1 semaine
        elif any(ext in request.path for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.woff', '.woff2', '.ttf']):
            response.headers['Cache-Control'] = 'public, max-age=604800, immutable'  # 7 jours
        # Cache les CSS/JS pendant 1 jour
        elif any(ext in request.path for ext in ['.css', '.js']):
            response.headers['Cache-Control'] = 'public, max-age=86400'  # 1 jour
        else:
            response.headers['Cache-Control'] = 'public, max-age=3600'  # 1h par défaut pour le reste
    else:
        # Pas de cache pour les pages HTML dynamiques
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


def add_default_rewards_if_empty():
    """
    Fonction désactivée - les récompenses par défaut ne sont plus ajoutées automatiquement
    L'ajout de tâches reste actif via les autres fonctions
    """
    pass


add_default_rewards_if_empty()

def get_user_points(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE email=?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def compute_daily_streak(conn, email):
    """Calcule le streak (jours consécutifs) pour un utilisateur basé sur completed_tasks."""
    try:
        c = conn.cursor()
        # Récupérer les dates distinctes où l'utilisateur a complété au moins une tâche
        c.execute("""
            SELECT DISTINCT DATE(completed_at) as d
            FROM completed_tasks
            WHERE user_email=?
            ORDER BY d DESC
        """, (email,))
        dates = [row[0] for row in c.fetchall()]
        if not dates:
            return 0
        from datetime import date, timedelta
        streak = 0
        current = date.today()
        # Compter à rebours tant que la date existe dans la liste
        while True:
            dstr = current.isoformat()
            if dstr in dates:
                streak += 1
                current = current - timedelta(days=1)
            else:
                break
        return streak
    except Exception:
        return 0

def propagate_player_name_change(cursor, email, old_name, new_name, house_id):
    """
    Propage le changement de pseudo d'un joueur partout dans la base.
    Met à jour :
    - Le contenu des messages (notifications maison, baby_tracking, task_added, privés...)
    - Le champ sender_email quand il contient l'ancien nom (messages house non-email)
    - Les commentaires de la maison contenant l'ancien nom
    """
    if not old_name or not new_name or old_name == new_name:
        return 0
    
    updated_count = 0
    try:
        # 1. Mettre à jour le CONTENU des messages de la maison qui contiennent l'ancien nom
        cursor.execute("""
            UPDATE messages 
            SET content = REPLACE(content, ?, ?)
            WHERE house_id = ? AND content LIKE ?
        """, (old_name, new_name, house_id, f'%{old_name}%'))
        updated_count += cursor.rowcount
        
        # 2. Mettre à jour sender_email quand c'est un nom (pas un email) pour les messages house
        #    Ex: sender_email = "Marguerite" au lieu d'un email pour certains messages
        cursor.execute("""
            UPDATE messages 
            SET sender_email = REPLACE(sender_email, ?, ?)
            WHERE house_id = ? AND sender_type = 'house' 
            AND sender_email NOT LIKE '%@%'
            AND sender_email LIKE ?
        """, (old_name, new_name, house_id, f'%{old_name}%'))
        updated_count += cursor.rowcount
        
        # 3. Mettre à jour les commentaires contenant l'ancien nom
        #    (commentaires écrits par ce joueur ET commentaires mentionnant ce joueur)
        cursor.execute("""
            UPDATE comments 
            SET content = REPLACE(content, ?, ?)
            WHERE content LIKE ?
            AND user_email IN (SELECT email FROM users WHERE house_id = ?)
        """, (old_name, new_name, f'%{old_name}%', house_id))
        updated_count += cursor.rowcount
        
        _dbg(f"✅ Propagation du changement de nom: '{old_name}' → '{new_name}' pour {email} dans maison {house_id} ({updated_count} entrées mises à jour)")
    except Exception as e:
        _dbg(f"⚠️ Erreur lors de la propagation du changement de nom: {e}")
    
    return updated_count


def create_system_message(house_id, content, message_type='system', related_task_id=None, send_push=True, sender_name=None, sender_email=None, related_category=None):
    """
    Crée un message système automatique pour la maison.
    Types: 'system', 'task_completed', 'task_added', 'congratulation', 'reminder', 'sermon', 'baby_tracking', 'courses_added'
    
    Si send_push=True, envoie également une notification push aux membres de la maison.
    sender_name: nom personnalisé pour l'expéditeur (ex: nom de la maison)
    sender_email: email du joueur pour les messages baby_tracking
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Pour les messages baby_tracking et task_added, utiliser l'email du joueur
        if message_type in ('baby_tracking', 'task_added', 'courses_added') and sender_email:
            actual_sender = sender_email
        else:
            # Utiliser le nom de la maison ou un nom par défaut
            if sender_name is None:
                c.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
                house_row = c.fetchone()
                if house_row:
                    sender_name = house_row[0] if house_row[0] else house_row[1]
                if not sender_name:
                    sender_name = "Maison"
            actual_sender = sender_name
        
        c.execute("""
            INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, related_task_id, related_category)
            VALUES (?, ?, 'house', ?, ?, ?, ?)
        """, (house_id, actual_sender, content, message_type, related_task_id, related_category))
        message_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # � Synchroniser la messagerie pour tous les utilisateurs de la maison
        if SOCKETIO_AVAILABLE and socketio:
            safe_socketio_emit('messages_list_update', {
                'house_id': house_id,
                'action': 'system_message',
                'message_type': message_type,
                'sender_name': sender_name
            }, room=f'house_{house_id}', namespace='/', broadcast=True)
            _dbg(f"🔌 WebSocket: Synchronisation messagerie système pour house_{house_id}")
        
        # �🔔 Envoyer une notification push si activé
        if send_push:
            try:
                # Déterminer l'icône et le titre selon le type
                notification_icons = {
                    'task_completed': '✅',
                    'task_added': '🆕',
                    'congratulation': '🎉',
                    'reminder': '⏰',
                    'sermon': '🏠',
                    'baby_tracking': '👶',
                    'courses_added': '🛒'
                }
                icon_emoji = notification_icons.get(message_type, '💬')
                
                # URL de destination selon le type
                notification_urls = {
                    'baby_tracking': '/menu',
                }
                notif_url = notification_urls.get(message_type, '/menu')
                
                # Titre personnalisé pour les messages de la maison
                if message_type in ['sermon', 'congratulation', 'reminder']:
                    title = f'{icon_emoji} {sender_name or "Maison"}'
                else:
                    title = f'{icon_emoji} Dust'
                
                notification_data = {
                    'title': title,
                    'body': content,
                    'icon': '/static/images/logo.png',
                    'url': notif_url,
                    'messageId': message_id,
                    'messageType': message_type,
                    'badge': 1
                }
                
                # Envoyer à tous les membres de la maison (sauf l'expéditeur si c'est un vrai utilisateur)
                exclude = sender_email if message_type in ('task_added', 'courses_added', 'baby_tracking') else None
                notify_house_members(house_id, notification_data, exclude_email=exclude)
                
            except Exception as e:
                print(f"⚠️ Erreur envoi notification push: {e}", flush=True)
        
        return True
    except Exception as e:
        print(f"Erreur création message système: {e}", flush=True)
        return False

def get_unread_message_count(user_email, house_id, existing_conn=None):
    """
    ✅ LOGIQUE MESSAGERIE SIMPLIFIÉE:
    Retourne le nombre de messages privés reçus par cet utilisateur qui ne sont PAS encore lus.
    
    IMPORTANT: Ne compte QUE les messages reçus par cette personne.
    - Pastille sur avatar utilisateur = messages reçus non lus (visible sur son téléphone uniquement)
    - Pour les enfants, utiliser get_children_unread_counts() (visible par tous)
    """
    try:
        _own = existing_conn is None
        conn = existing_conn if existing_conn else get_db_connection()
        c = conn.cursor()
        
        # Compter uniquement les messages reçus par cet utilisateur qui ne sont pas encore marqués comme lus
        c.execute("""
            SELECT COUNT(*) FROM messages m
            WHERE m.house_id = ?
            AND m.recipient_email = ?
            AND m.message_type = 'private'
            AND NOT EXISTS (
                SELECT 1 FROM message_reads mr 
                WHERE mr.message_id = m.id 
                AND mr.user_email = ?
            )
        """, (house_id, user_email, user_email))
        
        count = c.fetchone()[0]
        if _own:
            conn.close()
        return count
    except Exception as e:
        _dbg(f"❌ Erreur get_unread_message_count: {e}")
        return 0

def get_children_unread_counts(house_id, existing_conn=None):
    """
    ✅ LOGIQUE ENFANTS SANS TÉLÉPHONE:
    Retourne un dict {child_email: count} des messages reçus non lus pour TOUS les enfants de la maison.
    Ces pastilles sont visibles par TOUS les adultes de la maison.
    
    Si existing_conn est fourni, réutilise cette connexion (ne la ferme pas).
    """
    try:
        _own = existing_conn is None
        conn = existing_conn if existing_conn else get_db_connection()
        c = conn.cursor()
        
        # Pour chaque enfant de la maison, compter ses messages non lus
        c.execute("""
            SELECT u.email, COUNT(m.id) as unread_count
            FROM users u
            LEFT JOIN messages m ON m.recipient_email = u.email 
                AND m.house_id = ? 
                AND m.message_type = 'private'
                AND NOT EXISTS (
                    SELECT 1 FROM message_reads mr 
                    WHERE mr.message_id = m.id 
                    AND mr.user_email = u.email
                )
            WHERE u.house_id = ?
            AND u.is_child_account = 1
            GROUP BY u.email
        """, (house_id, house_id))
        
        children_unread = {email: count for email, count in c.fetchall()}
        if _own:
            conn.close()
        return children_unread
    except Exception as e:
        _dbg(f"❌ Erreur get_children_unread_counts: {e}")
        return {}

def get_unread_messages_by_sender(user_email, house_id, existing_conn=None):
    """
    ⚠️ FONCTION DEPRECATED - À SUPPRIMER
    Utiliser get_unread_message_count() et get_children_unread_counts() à la place.
    """
    return {}

def get_unread_count_by_type(user_email, house_id, message_type, existing_conn=None, include_own=False):
    """
    Retourne le nombre de messages non lus d'un type donné (baby_tracking, task_added, courses_added, etc).
    Exclut les messages envoyés par l'utilisateur lui-même (on ne se notifie pas soi-même).
    Si existing_conn est fourni, réutilise cette connexion (ne la ferme pas).
    """
    try:
        _own = existing_conn is None
        conn = existing_conn if existing_conn else get_db_connection()
        c = conn.cursor()
        if include_own:
            c.execute("""
                SELECT COUNT(*) FROM messages m
                WHERE m.house_id = ?
                AND m.message_type = ?
                AND NOT EXISTS (
                    SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?
                )
            """, (house_id, message_type, user_email))
        else:
            c.execute("""
                SELECT COUNT(*) FROM messages m
                WHERE m.house_id = ?
                AND m.message_type = ?
                AND (m.sender_email IS NULL OR m.sender_email != ?)
                AND NOT EXISTS (
                    SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?
                )
            """, (house_id, message_type, user_email, user_email))
        count = c.fetchone()[0]
        if _own:
            conn.close()
        return count
    except Exception:
        return 0

def get_unread_messages_sent_to(user_email, house_id, existing_conn=None):
    """
    ⚠️ FONCTION DEPRECATED - À SUPPRIMER
    Utiliser get_unread_message_count() et get_children_unread_counts() à la place.
    """
    return {}

def mark_message_as_read(message_id, user_email):
    """
    Marque un message comme lu pour un utilisateur.
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO message_reads (message_id, user_email)
            VALUES (?, ?)
            ON CONFLICT(message_id, user_email) DO NOTHING
        """, (message_id, user_email))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        _dbg(f"❌ mark_message_as_read échoué: message_id={message_id}, user_email={user_email}, err={e}")
        return False


# 🔔 ========== FONCTIONS PUSH NOTIFICATIONS ==========

def save_push_subscription(user_email, subscription_data):
    """
    Sauvegarde une subscription push pour un utilisateur.
    subscription_data doit contenir: endpoint, keys.p256dh, keys.auth
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        endpoint = subscription_data.get('endpoint', '')
        keys = subscription_data.get('keys', {})
        p256dh = keys.get('p256dh', '')
        auth = keys.get('auth', '')
        user_agent = subscription_data.get('userAgent', '')
        
        # Insérer ou mettre à jour
        c.execute("""
            INSERT INTO push_subscriptions (user_email, endpoint, p256dh_key, auth_key, user_agent, last_used)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_email, endpoint) 
            DO UPDATE SET 
                last_used = CURRENT_TIMESTAMP,
                is_active = 1
        """, (user_email, endpoint, p256dh, auth, user_agent))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        _dbg(f"❌ Erreur sauvegarde push subscription: {e}")
        return False


def get_user_push_subscriptions(user_email):
    """
    Récupère toutes les subscriptions push actives d'un utilisateur.
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT endpoint, p256dh_key, auth_key
            FROM push_subscriptions
            WHERE user_email = ? AND is_active = 1
        """, (user_email,))
        
        subscriptions = []
        for row in c.fetchall():
            subscriptions.append({
                'endpoint': row[0],
                'keys': {
                    'p256dh': row[1],
                    'auth': row[2]
                }
            })
        
        conn.close()
        return subscriptions
    except Exception as e:
        _dbg(f"❌ Erreur récupération subscriptions: {e}")
        return []


def get_house_push_subscriptions(house_id, exclude_email=None):
    """
    Récupère toutes les subscriptions push des membres d'une maison.
    exclude_email: optionnel, pour exclure l'expéditeur du message
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        if exclude_email:
            c.execute("""
                SELECT DISTINCT ps.endpoint, ps.p256dh_key, ps.auth_key, ps.user_email
                FROM push_subscriptions ps
                JOIN users u ON ps.user_email = u.email
                WHERE u.house_id = ? AND ps.is_active = 1 AND ps.user_email != ?
            """, (house_id, exclude_email))
        else:
            c.execute("""
                SELECT DISTINCT ps.endpoint, ps.p256dh_key, ps.auth_key, ps.user_email
                FROM push_subscriptions ps
                JOIN users u ON ps.user_email = u.email
                WHERE u.house_id = ? AND ps.is_active = 1
            """, (house_id,))
        
        subscriptions = []
        for row in c.fetchall():
            subscriptions.append({
                'endpoint': row[0],
                'keys': {
                    'p256dh': row[1],
                    'auth': row[2]
                },
                'user_email': row[3]
            })
        
        conn.close()
        return subscriptions
    except Exception as e:
        _dbg(f"❌ Erreur récupération subscriptions maison: {e}")
        return []


def send_push_notification(subscription, notification_data):
    """
    Envoie une notification push à un seul abonnement.
    Utilise la bibliothèque pywebpush (à installer: pip install pywebpush)
    
    notification_data: {
        'title': str,
        'body': str,
        'icon': str (optionnel),
        'url': str (optionnel),
        'messageId': int (optionnel)
    }
    """
    try:
        from pywebpush import webpush, WebPushException, Vapid
        from cryptography.hazmat.primitives.serialization import (
            load_pem_private_key, load_der_private_key, Encoding, PrivateFormat, NoEncryption
        )
        from cryptography.hazmat.backends import default_backend
        import json
        import base64

        # ── Lire les clés depuis les variables d'environnement ──────────────
        vapid_private_b64 = os.environ.get('VAPID_PRIVATE_KEY_B64', '')
        vapid_public_b64  = os.environ.get('VAPID_PUBLIC_KEY_B64', '')

        if vapid_private_b64 and vapid_public_b64:
            raw_priv = base64.b64decode(vapid_private_b64)
            raw_pub  = base64.b64decode(vapid_public_b64)
            # Le décodage peut donner des bytes bruts (32 octets) OU du texte PEM/DER
            try:
                VAPID_PRIVATE_KEY = raw_priv.decode('utf-8')
                VAPID_PUBLIC_KEY  = raw_pub.decode('utf-8')
            except Exception:
                # Bytes non-UTF8 → clé brute en base64url
                VAPID_PRIVATE_KEY = base64.urlsafe_b64encode(raw_priv).rstrip(b'=').decode('ascii')
                VAPID_PUBLIC_KEY  = base64.urlsafe_b64encode(raw_pub).rstrip(b'=').decode('ascii')
        else:
            VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
            VAPID_PUBLIC_KEY  = os.environ.get('VAPID_PUBLIC_KEY', '')

        # Remplacer les \n littéraux (backslash-n) par de vraies newlines
        VAPID_PRIVATE_KEY = VAPID_PRIVATE_KEY.replace('\\n', '\n').strip()
        VAPID_PUBLIC_KEY  = VAPID_PUBLIC_KEY.replace('\\n', '\n').strip()

        if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
            print("⚠️ VAPID keys non configurées", flush=True)
            return False

        # ── Normaliser la clé : détecter et décoder toutes les couches d'encodage ──
        # Cas confirmé sur Render : VAPID_PRIVATE_KEY contient le PEM encodé en base64 standard
        # (LS0tLS1C... = base64("-----BEGIN..."))
        def _decode_vapid_key(raw_str):
            """Renvoie la clé sous forme de string normalisée (PEM ou base64url)."""
            s = raw_str.replace('\\n', '\n').strip()
            # Déjà PEM ?
            if s.startswith('-----'):
                return s
            # Essayer base64 standard (la clé PEM pourrait être base64-encodée dans l'env var)
            for b64decode in [base64.b64decode, base64.urlsafe_b64decode]:
                try:
                    padding = 4 - len(s) % 4
                    candidate = s + ('=' * padding if padding != 4 else '')
                    decoded = b64decode(candidate)
                    try:
                        decoded_str = decoded.decode('utf-8').strip()
                        decoded_str = decoded_str.replace('\\n', '\n')
                        if decoded_str.startswith('-----'):
                            return decoded_str  # PEM encodé en base64 !
                    except Exception:
                        pass
                except Exception:
                    pass
            return s  # retourner tel quel (base64url raw)

        VAPID_PRIVATE_KEY = _decode_vapid_key(VAPID_PRIVATE_KEY)
        VAPID_PUBLIC_KEY  = VAPID_PUBLIC_KEY.replace('\\n', '\n').strip()

        if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
            print("⚠️ VAPID keys non configurées", flush=True)
            return False

        # ── Diagnostic exact du format après normalisation ────────────────────
        key_repr = repr(VAPID_PRIVATE_KEY[:60])
        print(f"🔑 VAPID key normalisée: {len(VAPID_PRIVATE_KEY)} chars, aperçu={key_repr}", flush=True)

        # ── Charger la clé ────────────────────────────────────────────────────
        vapid_obj = None
        priv_key_obj = None

        # Tentative 1 : format PEM (-----BEGIN...)
        if VAPID_PRIVATE_KEY.startswith('-----'):
            try:
                priv_key_obj = load_pem_private_key(VAPID_PRIVATE_KEY.encode('utf-8'), password=None)
                print("🔑 ✅ Format PEM chargé", flush=True)
            except Exception as e:
                print(f"🔑 ❌ PEM échoué: {e}", flush=True)

        # Tentative 2 : DER en base64url (format standard py_vapid)
        if priv_key_obj is None:
            try:
                # Ajouter padding si nécessaire
                k = VAPID_PRIVATE_KEY
                padding = 4 - len(k) % 4
                if padding != 4:
                    k += '=' * padding
                der_bytes = base64.urlsafe_b64decode(k)
                if len(der_bytes) == 32:
                    raise ValueError("raw key, pas DER")
                priv_key_obj = load_der_private_key(der_bytes, password=None, backend=default_backend())
                print(f"🔑 ✅ Format DER base64url chargé ({len(der_bytes)} bytes)", flush=True)
            except Exception as e:
                print(f"🔑 ❌ DER échoué: {e}", flush=True)

        # Tentative 3 : raw 32 bytes en base64url
        if priv_key_obj is None:
            try:
                k = VAPID_PRIVATE_KEY
                padding = 4 - len(k) % 4
                if padding != 4:
                    k += '=' * padding
                raw_bytes = base64.urlsafe_b64decode(k)
                if len(raw_bytes) == 32:
                    from cryptography.hazmat.primitives.asymmetric.ec import derive_private_key, SECP256R1
                    import binascii
                    priv_key_obj = derive_private_key(
                        int(binascii.hexlify(raw_bytes), 16),
                        SECP256R1(), default_backend()
                    )
                    print(f"🔑 ✅ Format raw 32 bytes chargé", flush=True)
                else:
                    print(f"🔑 ❌ base64url décodé = {len(raw_bytes)} bytes (pas 32)", flush=True)
            except Exception as e:
                print(f"🔑 ❌ raw échoué: {e}", flush=True)

        if priv_key_obj is None:
            print("🔑 ❌ Impossible de charger la clé dans aucun format connu", flush=True)
            return False

        # Convertir en raw 32 bytes → Vapid.from_raw()
        # PrivateFormat.Raw n'est valide que pour OKP (X25519/Ed25519), pas pour EC.
        # Pour les clés EC (P-256 = SECP256R1), on extrait la valeur entière private_value.
        from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
        if isinstance(priv_key_obj, EllipticCurvePrivateKey):
            private_value_int = priv_key_obj.private_numbers().private_value
            raw_key = private_value_int.to_bytes(32, 'big')
        else:
            raw_key = priv_key_obj.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        b64url_raw = base64.urlsafe_b64encode(raw_key).rstrip(b'=')
        vapid_obj = Vapid.from_raw(b64url_raw)
        print(f"🔑 ✅ Vapid chargé ({len(raw_key)} bytes raw)", flush=True)

        # ── Envoi ────────────────────────────────────────────────────────────
        vapid_email = os.environ.get('VAPID_EMAIL', 'mailto:contact@cleanbeat.app')
        VAPID_CLAIMS = {"sub": vapid_email}
        payload = json.dumps(notification_data)

        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=vapid_obj,
            vapid_claims=VAPID_CLAIMS
        )

        endpoint_short = subscription.get('endpoint', '')[:60]
        print(f"✅ Push envoyé → {endpoint_short}", flush=True)
        return True

    except WebPushException as e:
        status_code = None
        try:
            if hasattr(e, 'response') and e.response is not None:
                status_code = getattr(e.response, 'status_code', None)
        except Exception:
            pass
        print(f"❌ WebPush erreur (status={status_code}): {e}", flush=True)
        if status_code in (404, 410):
            deactivate_push_subscription(subscription.get('endpoint'))
        return False
    except ImportError:
        print("⚠️ pywebpush non installé", flush=True)
        return False
    except Exception as e:
        import traceback
        print(f"❌ Erreur envoi push inattendue: {e}", flush=True)
        traceback.print_exc()
        return False


def deactivate_push_subscription(endpoint):
    """
    Désactive une subscription push (quand elle est invalide/expirée).
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE push_subscriptions
            SET is_active = 0
            WHERE endpoint = ?
        """, (endpoint,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def notify_house_members(house_id, notification_data, exclude_email=None):
    """
    Envoie une notification push à tous les membres d'une maison.
    Calcule le badge count réel par utilisateur pour mettre à jour l'icône d'accueil.
    
    notification_data: {
        'title': str,
        'body': str,
        'icon': str (optionnel),
        'url': str (optionnel),
        'messageId': int (optionnel)
    }
    exclude_email: email de l'expéditeur à exclure
    """
    subscriptions = get_house_push_subscriptions(house_id, exclude_email)
    print(f"🔔 notify_house_members: house_id={house_id}, {len(subscriptions)} subscription(s) trouvée(s), exclude={exclude_email}", flush=True)
    
    success_count = 0
    for sub in subscriptions:
        user_email = sub.get('user_email')
        # Calculer le badge count réel pour cet utilisateur
        personalized_data = dict(notification_data)
        if user_email:
            try:
                total = (
                    get_unread_message_count(user_email, house_id) +
                    get_unread_count_by_type(user_email, house_id, 'baby_tracking') +
                    get_unread_count_by_type(user_email, house_id, 'task_added') +
                    get_unread_count_by_type(user_email, house_id, 'courses_added')
                )
                personalized_data['badge'] = max(1, total)
            except Exception:
                personalized_data['badge'] = 1
        if send_push_notification(sub, personalized_data):
            success_count += 1
    
    print(f"🔔 notify_house_members: {success_count}/{len(subscriptions)} push envoyé(s)", flush=True)
    return success_count


# 🔔 ========== FIN FONCTIONS PUSH NOTIFICATIONS ==========


# 💬 ========== SYSTÈME DE RAPPELS ET PERSONNALITÉ MAISON ==========

import random

# Messages de personnalité de la maison par type
HOUSE_MESSAGES = {
    'congratulation': [
        "🎉 Bravo {name} ! Tu cartonnes aujourd'hui !",
        "✨ Super boulot {name} ! La maison brille grâce à toi !",
        "🌟 {name}, tu es au top ! Continue comme ça !",
        "🏆 Chapeau {name} ! Quelle efficacité !",
        "💪 {name}, tu assures grave ! Respect !",
        "🎊 Waouh {name} ! Tu es sur une lancée incroyable !",
        "⭐ {name}, c'est toi la star du jour !",
    ],
    'encouragement': [
        "💙 Courage {name} ! Chaque petit geste compte !",
        "🌈 {name}, tu progresses, c'est super !",
        "☀️ Allez {name}, un petit effort et ce sera nickel !",
        "🌸 {name}, tu y es presque ! On croit en toi !",
        "💚 {name}, prends ton temps, l'important c'est de participer !",
    ],
    'reminder_gentle': [
        "🏠 Qui s'occupe du ménage aujourd'hui ? 🤔",
        "✨ La maison attend son champion du jour !",
        "🧹 C'est l'heure de faire briller la maison ! 💫",
        "🌟 Petite mission du jour : rendre la maison encore plus belle !",
        "🏡 Qui veut marquer des points aujourd'hui ? 😊",
    ],
    'reminder_funny': [
        "🤖 Alerte ! Les moutons de poussière préparent une révolte ! 🐑",
        "👻 Psst... la vaisselle dit qu'elle se sent seule...",
        "🎭 Breaking news : le sol réclame un coup de balai !",
        "🎪 Spectacle ce soir : qui relèvera le défi du ménage ?",
        "🎮 Mission disponible ! XP et points à gagner ! 🏆",
        "🦸 Recherche superhéros pour sauver la maison de la poussière !",
    ],
    'reminder_competitive': [
        "🏁 Qui sera le champion de la semaine ? Le suspense est total !",
        "⚡ La compétition s'intensifie ! Qui prendra la tête ?",
        "🎯 Objectif du jour : dominer le classement ! Qui relève le défi ?",
        "🔥 C'est le moment de faire la différence sur le leaderboard !",
        "💎 Des points faciles à grappiller aujourd'hui ! Qui se lance ?",
    ],
    'milestone': [
        "🎊 100 tâches complétées dans la maison ! Vous êtes incroyables !",
        "🏅 Record battu ! La maison n'a jamais été aussi propre !",
        "🌟 Semaine exceptionnelle ! Vous formez une super équipe !",
        "🎉 Félicitations à toute la maison ! Quel travail d'équipe !",
    ],
    'weekend': [
        "🎈 C'est le week-end ! Un petit coup de propre avant de se détendre ?",
        "☀️ Bon week-end ! On garde la maison nickel pour en profiter !",
        "🎉 Week-end mode ON ! Mais n'oublions pas les petites tâches !",
    ],
    'sermon_lazy': [
        "🏠 Euh... je ne veux pas être désagréable mais... ça fait 3 jours que personne ne fait rien ! 😅",
        "🏠 Les amis, je commence à ressembler à une maison hantée... Un petit coup de balai ? 👻",
        "🏠 Je ne suis pas une maison auto-nettoyante hein ! Qui vient m'aider ? 🧹",
        "🏠 Alors là, chapeau ! Vous battez des records... d'inactivité ! 😂",
        "🏠 Je vais finir par me mettre en grève si ça continue comme ça ! 🪧",
        "🏠 Les copains, la poussière organise une fête chez moi... Intervention requise ! 🎉🧹",
        "🏠 Bon, qui a mis le mode pause sur l'application ? On reprend le jeu ! 🎮",
        "🏠 Attention : niveau de saleté critique ! Envoyez les renforts ! 🚨",
        "🏠 Je rêve ou vous avez oublié que j'existe ? 😢 Revenez vite !",
        "🏠 SOS ! La vaisselle sale prépare une révolution ! Qui vient négocier ? 🍽️",
    ],
    'sermon_funny': [
        "🏠 {name}, tu te caches ou quoi ? Ça fait un bail ! 🕵️",
        "🏠 {name}, j'ai failli t'oublier ! Tu existes encore ? 😜",
        "🏠 {name}, je t'ai vu passer mais tu as fait zéro tâche ! C'est une technique ninja ? 🥷",
        "🏠 Alors {name}, on prend des vacances ? 🏖️ (Sans moi apparemment...)",
        "🏠 {name}, tu joues à cache-cache avec le ménage ? Tu gagnes ! 🙈",
        "🏠 {name}, je croyais qu'on était amis... mais tu m'abandonnes ! 💔",
        "🏠 {name}, même les plantes en font plus que toi ! Et elles bougent pas ! 🪴😂",
        "🏠 {name}, tu attends que je fasse le ménage toute seule ? Spoiler : je sais pas ! 🤷",
    ]
}


def send_house_encouragement(house_id, player_name=None):
    """
    Envoie un message d'encouragement de la maison à tous les joueurs.
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer le nom de la maison
        c.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
        house_row = c.fetchone()
        house_name = house_row[0] if (house_row and house_row[0]) else (house_row[1] if house_row else "Maison")
        
        # Choisir un message approprié
        if player_name:
            message = get_house_personality_message('congratulation', player_name=player_name, house_name=house_name)
        else:
            message = get_house_personality_message('encouragement', house_name=house_name)
        
        # Créer le message avec l'avatar de la maison
        create_system_message(
            house_id=house_id,
            content=message,
            message_type='congratulation' if player_name else 'encouragement',
            send_push=True,
            sender_name=f"🏠 {house_name}"
        )
        
        conn.close()
        return True
    except Exception as e:
        _dbg(f"❌ Erreur envoi encouragement maison: {e}")
        return False


def send_house_sermon(house_id, player_name=None, sermon_type='lazy'):
    """
    Envoie un message humoristique de réprimande de la maison.
    sermon_type: 'lazy' (inactivité générale) ou 'funny' (ciblé sur un joueur)
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer le nom de la maison
        c.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
        house_row = c.fetchone()
        house_name = house_row[0] if (house_row and house_row[0]) else (house_row[1] if house_row else "Maison")
        
        # Choisir un message approprié
        message_key = 'sermon_funny' if player_name and sermon_type == 'funny' else 'sermon_lazy'
        message = get_house_personality_message(message_key, player_name=player_name, house_name=house_name)
        
        # Créer le message avec l'avatar de la maison
        create_system_message(
            house_id=house_id,
            content=message,
            message_type='sermon',
            send_push=True,
            sender_name=f"🏠 {house_name}"
        )
        
        conn.close()
        return True
    except Exception as e:
        _dbg(f"❌ Erreur envoi sermon maison: {e}")
        return False


def check_house_activity_and_send_message(house_id):
    """
    Vérifie l'activité de la maison et envoie un message approprié.
    - Si aucune activité depuis 3 jours : sermon général
    - Si un joueur inactif depuis longtemps : sermon personnalisé
    - Si beaucoup d'activité : encouragement
    """
    try:
        from datetime import datetime, timedelta
        conn = get_db_connection()
        c = conn.cursor()
        
        # Vérifier l'activité récente (dernières 72h)
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        
        c.execute("""
            SELECT COUNT(*) FROM tasks 
            WHERE house_id=? AND completed=1 AND completed_at > ?
        """, (house_id, three_days_ago))
        
        recent_tasks = c.fetchone()[0]
        
        # Si pas d'activité récente, envoyer un sermon général
        if recent_tasks == 0:
            conn.close()
            return send_house_sermon(house_id, sermon_type='lazy')
        
        # Si beaucoup d'activité (>10 tâches en 3 jours), envoyer encouragement
        elif recent_tasks > 10:
            # Trouver le joueur le plus actif
            c.execute("""
                SELECT u.name, COUNT(*) as task_count
                FROM tasks t
                JOIN users u ON t.completed_by = u.email
                WHERE t.house_id=? AND t.completed=1 AND t.completed_at > ?
                GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style
                ORDER BY task_count DESC
                LIMIT 1
            """, (house_id, three_days_ago))
            
            top_player = c.fetchone()
            player_name = top_player[0] if top_player else None
            conn.close()
            return send_house_encouragement(house_id, player_name=player_name)
        
        conn.close()
        return False
        
    except Exception as e:
        _dbg(f"❌ Erreur vérification activité maison: {e}")
        return False


# 💬 ========== FIN SYSTÈME DE RAPPELS ET PERSONNALITÉ MAISON ==========

def get_house_personality_message(message_type, player_name=None, house_name=None):
    """
    Génère un message de personnalité de la maison.
    
    message_type: 'congratulation', 'encouragement', 'reminder_gentle', 
                  'reminder_funny', 'reminder_competitive', 'milestone', 'weekend'
    player_name: nom du joueur (optionnel, pour messages personnalisés)
    house_name: nom de la maison (optionnel)
    """
    messages = HOUSE_MESSAGES.get(message_type, HOUSE_MESSAGES['reminder_gentle'])
    message = random.choice(messages)
    
    # Remplacer les variables
    if player_name and '{name}' in message:
        message = message.replace('{name}', player_name)
    if house_name and '{house}' in message:
        message = message.replace('{house}', house_name)
    
    return message


def create_reminder(house_id, reminder_type, scheduled_for=None):
    """
    Crée un rappel programmé pour une maison.
    
    reminder_type: type de message à envoyer
    scheduled_for: datetime ou string ISO, si None = maintenant + 1h
    """
    try:
        from datetime import datetime, timedelta
        
        if scheduled_for is None:
            scheduled_for = datetime.now() + timedelta(hours=1)
        elif isinstance(scheduled_for, str):
            scheduled_for = datetime.fromisoformat(scheduled_for)
        
        # Générer le message
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer le nom de la maison
        c.execute("SELECT name FROM houses WHERE id=?", (house_id,))
        house_row = c.fetchone()
        house_name = house_row[0] if house_row else "votre maison"
        
        message = get_house_personality_message(reminder_type, house_name=house_name)
        
        # Créer le rappel
        c.execute("""
            INSERT INTO reminders (house_id, reminder_type, message, scheduled_for)
            VALUES (?, ?, ?, ?)
        """, (house_id, reminder_type, message, scheduled_for.isoformat()))
        
        reminder_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return reminder_id
    except Exception as e:
        _dbg(f"❌ Erreur création reminder: {e}")
        return None


def get_pending_reminders():
    """
    Récupère les rappels en attente d'envoi.
    """
    from datetime import datetime
    
    conn = get_db_connection()
    c = conn.cursor()
    
    now = datetime.now().isoformat()
    c.execute("""
        SELECT id, house_id, reminder_type, message, scheduled_for
        FROM reminders
        WHERE is_sent = 0 AND scheduled_for <= ?
        ORDER BY scheduled_for ASC
    """, (now,))
    
    reminders = []
    for row in c.fetchall():
        reminders.append({
            'id': row[0],
            'house_id': row[1],
            'reminder_type': row[2],
            'message': row[3],
            'scheduled_for': row[4]
        })
    
    conn.close()
    return reminders


def send_reminder(reminder_id):
    """
    Envoie un rappel via le système de messagerie.
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer le rappel
        c.execute("""
            SELECT house_id, message, reminder_type
            FROM reminders WHERE id=?
        """, (reminder_id,))
        
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        
        house_id, message, reminder_type = row
        
        # Créer le message système
        create_system_message(
            house_id=house_id,
            content=message,
            message_type='reminder',
            send_push=True
        )
        
        # Marquer comme envoyé
        from datetime import datetime
        c.execute("""
            UPDATE reminders 
            SET is_sent = 1, sent_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), reminder_id))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        _dbg(f"❌ Erreur envoi reminder: {e}")
        return False


def process_pending_reminders():
    """
    Traite tous les rappels en attente.
    À appeler périodiquement (cron, scheduler, etc.)
    """
    reminders = get_pending_reminders()
    sent_count = 0
    
    for reminder in reminders:
        if send_reminder(reminder['id']):
            sent_count += 1
    
    return sent_count


def get_user_reminder_settings(user_email):
    """
    Récupère les préférences de rappel d'un utilisateur.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT reminders_enabled, reminder_frequency, quiet_hours_start, quiet_hours_end
        FROM user_reminder_settings
        WHERE user_email = ?
    """, (user_email,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'enabled': bool(row[0]),
            'frequency': row[1],
            'quiet_hours_start': row[2],
            'quiet_hours_end': row[3]
        }
    else:
        # Valeurs par défaut
        return {
            'enabled': True,
            'frequency': 'daily',
            'quiet_hours_start': '22:00',
            'quiet_hours_end': '08:00'
        }


def update_user_reminder_settings(user_email, enabled=None, frequency=None, quiet_hours_start=None, quiet_hours_end=None):
    """
    Met à jour les préférences de rappel d'un utilisateur.
    """
    try:
        from datetime import datetime
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Vérifier si l'utilisateur a déjà des settings
        c.execute("SELECT id FROM user_reminder_settings WHERE user_email=?", (user_email,))
        exists = c.fetchone()
        
        if exists:
            # UPDATE
            updates = []
            params = []
            
            if enabled is not None:
                updates.append("reminders_enabled = ?")
                params.append(1 if enabled else 0)
            if frequency is not None:
                updates.append("reminder_frequency = ?")
                params.append(frequency)
            if quiet_hours_start is not None:
                updates.append("quiet_hours_start = ?")
                params.append(quiet_hours_start)
            if quiet_hours_end is not None:
                updates.append("quiet_hours_end = ?")
                params.append(quiet_hours_end)
            
            if updates:
                updates.append("last_updated = ?")
                params.append(datetime.now().isoformat())
                params.append(user_email)
                
                query = f"UPDATE user_reminder_settings SET {', '.join(updates)} WHERE user_email = ?"
                c.execute(query, params)
        else:
            # INSERT
            c.execute("""
                INSERT INTO user_reminder_settings 
                (user_email, reminders_enabled, reminder_frequency, quiet_hours_start, quiet_hours_end)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_email,
                1 if (enabled if enabled is not None else True) else 0,
                frequency if frequency else 'daily',
                quiet_hours_start if quiet_hours_start else '22:00',
                quiet_hours_end if quiet_hours_end else '08:00'
            ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        _dbg(f"❌ Erreur update reminder settings: {e}")
        return False


# 💬 ========== FIN SYSTÈME DE RAPPELS ==========


def validate_avatar_file(avatar_file_value):
    """Vérifie si un fichier avatar existe réellement sur le disque.
    Retourne le nom du fichier si trouvé, None sinon."""
    if not avatar_file_value or avatar_file_value == 'None':
        return None
    # Vérifier dans static/avatars/
    if os.path.exists(os.path.join('static', 'avatars', avatar_file_value)):
        return avatar_file_value
    # Fichier introuvable → retourner None pour fallback DiceBear
    _dbg(f"[AVATAR] Fichier '{avatar_file_value}' introuvable → fallback")
    return None


def get_house_players_points(house_id, existing_conn=None):
    """
    Retourne une liste de dictionnaires avec les joueurs de la maison.
    Inclut automatiquement les daily_points (points du jour) et daily_tasks.
    Si existing_conn est fourni, réutilise cette connexion (ne la ferme pas).
    """
    _own_conn = existing_conn is None
    conn = existing_conn if existing_conn else get_db_connection()
    c = conn.cursor()
    today = date.today().isoformat()
    
    # Récupérer tous les champs nécessaires pour les avatars
    c.execute("""
        SELECT email, points, avatar, avatar_file, avatar_url, name, player_color, avatar_style, is_child_account,
               COALESCE(skull_count, 0), skull_expires_at, bonus_expires_at
        FROM users WHERE house_id=?
    """, (house_id,))
    rows = c.fetchall()
    players = []

    # 🚀 BATCH: skull_pending pour tous les joueurs en 1 requête
    _skull_pending_map = set()  # emails accusés (proof_request pending)
    _skull_active_map = {}  # {email: bool}
    try:
        from datetime import datetime as _dt
        c.execute("""
            SELECT DISTINCT target_email FROM proof_requests
            WHERE house_id=? AND status='pending'
        """, (house_id,))
        for row_sp in c.fetchall():
            _skull_pending_map.add(row_sp[0])
    except Exception:
        pass

    # 🚀 BATCH: suspicion_active pour tous les joueurs en 1 requête
    # Compter UNIQUEMENT les joueurs SOUPÇONNÉS (qui doivent prouver leur tâche)
    # La loupe 🔍 n'apparaît QUE sur l'avatar du joueur soupçonné
    _suspicion_count_map = {}  # {email: count}
    try:
        # UNIQUEMENT joueur soupçonné (doit uploader photo)
        c.execute("""
            SELECT suspected_player_email, COUNT(*)
            FROM suspicions
            WHERE house_id=? AND status IN ('pending', 'awaiting_validation')
            GROUP BY suspected_player_email
        """, (house_id,))
        for row_susp in c.fetchall():
            _suspicion_count_map[row_susp[0]] = int(row_susp[1])
    except Exception:
        pass

    # 🚀 BATCH: calculer daily_points pour TOUS les joueurs en 1 seule requête
    _daily_map = {}  # {email: (points, tasks)}
    try:
        c.execute("""
            SELECT user_email, COALESCE(SUM(points),0), COUNT(*)
            FROM completed_tasks
            WHERE house_id=? AND DATE(completed_at)=?
            GROUP BY user_email
        """, (house_id, today))
        for row_dp in c.fetchall():
            _daily_map[row_dp[0]] = (int(row_dp[1]) if row_dp[1] else 0, int(row_dp[2]) if row_dp[2] else 0)
    except Exception:
        pass
    
    for r in rows:
        email = r[0]
        points = r[1]
        avatar_emoji = r[2]
        avatar_file = r[3]
        avatar_url = r[4]
        name = r[5] if r[5] else (email.split('@')[0] if email else '')
        player_color = r[6] if len(r) > 6 else None
        avatar_style = r[7] if len(r) > 7 else 'adventurer'  # Style DiceBear par défaut
        is_child_account = r[8] if len(r) > 8 else 0  # Statut enfant (0 = adulte, 1 = enfant)
        skull_count_raw = r[9] if len(r) > 9 else 0
        skull_expires_at_raw = r[10] if len(r) > 10 else None
        bonus_expires_at_raw = r[11] if len(r) > 11 else None
        # Crâne actif (malus ou tricherie prouvée)
        skull_active = False
        if skull_expires_at_raw:
            try:
                from datetime import datetime as _dt2
                skull_active = _dt2.fromisoformat(str(skull_expires_at_raw)) > _dt2.utcnow()
            except Exception:
                pass
        # Bonus actif (❤️)
        bonus_active = False
        if bonus_expires_at_raw:
            try:
                from datetime import datetime as _dt3
                bonus_active = _dt3.fromisoformat(str(bonus_expires_at_raw)) > _dt3.utcnow()
            except Exception:
                pass
        skull_pending = email in _skull_pending_map
        
        # Suspicion active (loupe 🔍)
        suspicion_count = _suspicion_count_map.get(email, 0)
        suspicion_active = suspicion_count > 0
        
        _dbg(f"\n🔍 Traitement joueur: {name} ({email}) - NOUVEAU CODE ACTIF!")
        _dbg(f"   avatar_emoji={avatar_emoji}, avatar_style={avatar_style}, avatar_url={avatar_url}, is_child={is_child_account}")
        
        # Assigner une couleur si le joueur n'en a pas encore
        if not player_color:
            player_color = assign_player_color(email, house_id)

        # Vérifier que avatar_emoji est bien un emoji et pas un nom de fichier/URL
        is_valid_emoji = False
        is_dicebear_seed = False
        if avatar_emoji:
            avatar_str = str(avatar_emoji).strip()
            _dbg(f"🔍 DEBUG {email}: avatar_str='{avatar_str}', len={len(avatar_str)}")
            # C'est un emoji si : max 4 caractères, contient des caractères Unicode > 127, 
            # et ne contient pas .png, .jpg, http, ou /
            if (len(avatar_str) <= 4 and 
                any(ord(c) > 127 for c in avatar_str) and
                '.png' not in avatar_str.lower() and 
                '.jpg' not in avatar_str.lower() and
                'http' not in avatar_str.lower() and
                '/' not in avatar_str):
                is_valid_emoji = True
                _dbg(f"✅ {email}: Détecté comme emoji")
            # C'est un seed DiceBear si : chaîne alphanumérique sans extension ni URL
            elif (len(avatar_str) >= 4 and 
                  '.' not in avatar_str and 
                  'http' not in avatar_str.lower() and
                  '/' not in avatar_str):
                is_dicebear_seed = True
                _dbg(f"✅ {email}: Détecté comme seed DiceBear")
            else:
                _dbg(f"⚠️ {email}: Aucune détection, len={len(avatar_str)}, has_dot={'.' in avatar_str}")

        # 🚀 Points du jour depuis le batch pré-calculé (0 requête DB ici)
        daily_points = _daily_map.get(email, (0, 0))[0]
        daily_tasks = _daily_map.get(email, (0, 0))[1]

        # Nettoyer avatar_file et avatar_url des valeurs "None" (chaîne)
        clean_avatar_file = avatar_file if avatar_file and avatar_file != 'None' else None
        clean_avatar_url = avatar_url if avatar_url and avatar_url != 'None' else None
        # Supprimer backgroundColor des URLs DiceBear (fond coloré indésirable dans le SVG)
        if clean_avatar_url and 'backgroundColor' in clean_avatar_url:
            import re as _re
            clean_avatar_url = _re.sub(r'[&?]backgroundColor=[^&]*', '', clean_avatar_url).rstrip('?&')

        # CORRECTION : Si la colonne 'avatar' contient une URL complète (données mal stockées)
        # Cas fréquent pour les enfants créés via invite_partner_new.html (DiceBear v8)
        if avatar_emoji and str(avatar_emoji).startswith('http') and not clean_avatar_url:
            clean_avatar_url = avatar_emoji
            # Supprimer le backgroundColor intégré dans l'URL (fond coloré indésirable)
            import re as _re
            clean_avatar_url = _re.sub(r'[&?]backgroundColor=[^&]*', '', clean_avatar_url).rstrip('?&')
            avatar_emoji = None
            is_valid_emoji = False
            is_dicebear_seed = False
            _dbg(f"🔧 URL complète trouvée dans colonne 'avatar' pour {name}: {clean_avatar_url}")
        
        # Vérifier que le fichier avatar existe RÉELLEMENT sur le disque
        if clean_avatar_file:
            avatar_path = os.path.join('static', 'avatars', clean_avatar_file)
            if not os.path.exists(avatar_path):
                _dbg(f"[DEBUG] avatar_file '{clean_avatar_file}' introuvable dans static/avatars/ → fallback pour {name}")
                clean_avatar_file = None
        
        # CORRECTION : Si avatar est vide mais avatar_url existe, extraire le seed ET le style de l'URL
        if not avatar_emoji and clean_avatar_url and 'seed=' in clean_avatar_url:
            try:
                import re
                seed_match = re.search(r'seed=([^&]+)', clean_avatar_url)
                if seed_match:
                    avatar_emoji = seed_match.group(1)
                    is_dicebear_seed = True
                    is_valid_emoji = False
                    _dbg(f"🔧 Seed extrait de l'URL pour {email}: {avatar_emoji}")
                
                # Extraire aussi le style de l'URL si avatar_style est vide
                if not avatar_style:
                    style_match = re.search(r'dicebear\.com/[^/]+/([^/]+)/', clean_avatar_url)
                    if style_match:
                        avatar_style = style_match.group(1)
                        _dbg(f"🔧 Style extrait de l'URL pour {email}: {avatar_style}")
                    else:
                        _dbg(f"⚠️ Pas de style trouvé dans l'URL pour {email}: {clean_avatar_url}")
                else:
                    _dbg(f"🔍 Style déjà défini pour {email}: {avatar_style}")
            except Exception as e:
                _dbg(f"⚠️ Erreur extraction seed/style: {e}")
                
        _dbg(f"🔍 DEBUG FINAL {email}: clean_avatar_url={clean_avatar_url}, is_dicebear_seed={is_dicebear_seed}, avatar_emoji={avatar_emoji}, avatar_style={avatar_style}")
        
        # Si c'est un seed DiceBear, reconstruire l'URL avec le bon style stocké
        if is_dicebear_seed and avatar_emoji:
            style = avatar_style if avatar_style else 'adventurer'
            new_url = f'https://api.dicebear.com/7.x/{style}/svg?seed={avatar_emoji}'
            _dbg(f"🔍 DEBUG RECONSTRUCTION: avatar_style={avatar_style}, style={style}, new_url={new_url}")
            
            # Ne reconstruire que si aucune URL DiceBear n'est déjà stockée
            # (évite d'écraser les URLs v8 avec backgroundColor des enfants créés via invite_partner_new)
            if clean_avatar_url and 'dicebear.com' in clean_avatar_url:
                # Supprimer le paramètre backgroundColor des URLs v8 (fond coloré indésirable)
                import re as _re
                clean_avatar_url = _re.sub(r'[&?]backgroundColor=[^&]*', '', clean_avatar_url)
                clean_avatar_url = clean_avatar_url.rstrip('?&')
                _dbg(f"✅ {email}: URL DiceBear conservée (backgroundColor supprimé): {clean_avatar_url}")
            elif not clean_avatar_url:
                _dbg(f"🔄 URL reconstruite pour {email}: {new_url} (style={style}, seed={avatar_emoji})")
                clean_avatar_url = new_url
            else:
                _dbg(f"🔄 URL reconstruite pour {email}: {new_url} (ancien non-DiceBear: {clean_avatar_url})")
                clean_avatar_url = new_url
        else:
            _dbg(f"⚠️ {email}: Pas de reconstruction URL (is_dicebear_seed={is_dicebear_seed}, avatar_emoji={avatar_emoji})")
        
        # Gérer les anciennes données incohérentes : si avatar_file existe
        # MAIS l'utilisateur a choisi un DiceBear/emoji plus récemment (avatar_url reconstruit)
        if clean_avatar_file and (is_dicebear_seed or is_valid_emoji) and clean_avatar_url:
            clean_avatar_file = None
        
        # Si aucun avatar n'est défini, générer une URL DiceBear par défaut basée sur l'email
        if not clean_avatar_url and not clean_avatar_file and not is_valid_emoji and not is_dicebear_seed:
            # Utiliser l'email comme seed pour DiceBear
            seed = email.split('@')[0] if email else 'default'
            style = avatar_style if avatar_style else 'adventurer'  # Utiliser le style stocké ou adventurer par défaut
            clean_avatar_url = f'https://api.dicebear.com/7.x/{style}/svg?seed={seed}'
        
        # Convertir la couleur hex en gradients pour correspondre au style du menu (v-bar verticale et horizontale)
        color_vertical = None
        color_horizontal = None
        if player_color and player_color.startswith('#'):
            # Extraire les composantes RGB du code hex
            hex_color = player_color.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                # Créer des gradients avec transparence pour l'effet visuel
                # Augmenter l'opacité pour améliorer la lisibilité (plus visible)
                color_vertical = f'linear-gradient(180deg, rgba({r}, {g}, {b}, 1.00) 0%, rgba({r}, {g}, {b}, 0.95) 100%)'
                color_horizontal = f'linear-gradient(90deg, rgba({r}, {g}, {b}, 1.00) 0%, rgba({r}, {g}, {b}, 0.95) 100%)'
        
        # DEBUG: Afficher les valeurs avant de les ajouter
        _dbg(f"🔍 DEBUG get_house_players: email={email}, avatar_emoji={avatar_emoji}, is_valid_emoji={is_valid_emoji}, is_dicebear_seed={is_dicebear_seed}, clean_avatar_url={clean_avatar_url}, clean_avatar_file={clean_avatar_file}")
        
        players.append({
            'email': email,
            'name': name,
            'avatar': avatar_emoji if (is_valid_emoji or is_dicebear_seed) else None,  # Emoji ou seed DiceBear
            'avatar_url': clean_avatar_url,  # URL si présente
            'avatar_file': clean_avatar_file,  # Fichier uploadé
            'avatar_style': avatar_style if avatar_style else 'adventurer',  # Style DiceBear
            'points': points,
            'daily_points': daily_points,
            'daily_tasks': daily_tasks,
            'color': color_vertical if color_vertical else player_color,  # Gradient pour v-bar verticale (ou hex en fallback)
            'color_h': color_horizontal if color_horizontal else player_color,  # Gradient pour v-bar horizontale (ou hex en fallback)
            'player_color_hex': player_color,  # Couleur hex brute pour bordure d'avatar
            'is_child_account': is_child_account,  # 0 = adulte, 1 = enfant (pour badges messagerie)
            'skull_count': int(skull_count_raw) if skull_count_raw else 0,
            'skull_active': skull_active,
            'skull_pending': skull_pending,
            'bonus_active': bonus_active,
            'suspicion_active': suspicion_active,
            'suspicion_count': suspicion_count,
        })

    if _own_conn:
        conn.close()
    return players



# ===============================
# ROUTES
# ===============================



# ===============================
# ROUTES
# ===============================



@app.route('/signup_email', methods=['GET', 'POST'])
def signup_email():
    """Inscription avec email - ÉTAPE 1 du parcours"""
    # Code d'invitation éventuel (joueur invité via SMS)
    invite_code = request.args.get('code', '').strip().upper() or session.get('invite_code', '')

    if request.method == 'POST':
        firstname = request.form.get('firstname', '').strip().capitalize()
        name = request.form.get('name', '').strip().capitalize()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        invite_code_form = request.form.get('invite_code', '').strip().upper()
        if invite_code_form:
            invite_code = invite_code_form

        # Validations de base
        if not firstname or not name or not email or not password:
            flash("Prénom, nom, email et mot de passe sont requis", "danger")
            return render_template('signup_email.html', invite_code=invite_code)

        if len(password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères", "danger")
            return render_template('signup_email.html', invite_code=invite_code)

        # Vérifier si email existe déjà
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT email, registration_step, password FROM users WHERE email=?", (email,))
        existing = c.fetchone()

        if existing:
            existing_step = existing[1] or ''
            existing_pw = existing[2] or ''
            # Si le compte existe mais l'inscription est incomplète (registration_step='email_signup'),
            # on autorise à reprendre / réinitialiser le compte avec les nouvelles infos
            if existing_step == 'email_signup':
                # Mettre à jour le compte incomplet avec les nouvelles données
                hashed_password = generate_password_hash(password)
                display_name = f"{firstname} {name}"
                c.execute("""
                    UPDATE users SET firstname=?, name=?, password=?, phone=?, avatar='👤'
                    WHERE email=?
                """, (firstname, display_name, hashed_password, phone, email))
                conn.commit()
                conn.close()

                session.permanent = True
                session['user'] = email
                session['user_name'] = display_name
                session['registration_step'] = 'email_signup'
                session.pop('invite_code', None)
                flash(f"Bienvenue {firstname} ! 🎉", "success")
                # Joueur principal: passer par le choix du type de foyer
                return redirect(url_for('choose_house_type'))
            else:
                # Compte complet → rediriger vers login
                flash("Cet email est déjà utilisé. Connecte-toi avec ton mot de passe.", "danger")
                conn.close()
                return redirect(url_for('login'))

        try:
            hashed_password = generate_password_hash(password)
            display_name = f"{firstname} {name}"

            # Si joueur invité : trouver la maison du code
            house_id_to_join = None
            if invite_code:
                c.execute("SELECT id FROM houses WHERE code=?", (invite_code,))
                house_row = c.fetchone()
                if house_row:
                    house_id_to_join = house_row[0]
                else:
                    # Code invalide : on bloque l'inscription
                    flash("🚫 Code d'invitation invalide. Vérifie le lien ou contacte la personne qui t'a invité.", "danger")
                    conn.close()
                    return render_template('signup_email.html', invite_code=invite_code)

            c.execute("""
                INSERT INTO users (firstname, name, email, password, phone, points, avatar, registration_step, house_id)
                VALUES (?, ?, ?, ?, ?, 0, '👤', 'email_signup', ?)
            """, (firstname, display_name, email, hashed_password, phone, house_id_to_join))

            conn.commit()
            conn.close()

            # Sauvegarder dans la session
            session.permanent = True
            session['user'] = email
            session['user_name'] = display_name
            session['registration_step'] = 'email_signup'
            session.pop('invite_code', None)

            flash(f"Bienvenue {firstname} ! 🎉", "success")

            # Joueur invité → directement create_profile
            if house_id_to_join:
                return redirect(url_for('create_profile'))

            # Joueur principal: étape dédiée de choix famille/couple/coloc
            return redirect(url_for('choose_house_type'))

        except _DBIntegrityError:
            flash("Erreur lors de la création du compte. Réessaie.", "danger")
            conn.close()
            return render_template('signup_email.html', invite_code=invite_code)

    # GET — conserver le code d'invitation dans la session si présent
    if invite_code:
        session['invite_code'] = invite_code

    return render_template('signup_email.html', invite_code=invite_code)
@app.route('/choose_house_type', methods=['GET', 'POST'])
def choose_house_type():
    """ÉTAPE 2 : Choix du type de logement"""
    if 'user' not in session:
        flash("Veuillez d'abord vous inscrire", "warning")
        return redirect(url_for('signup_email'))
    
    if request.method == 'POST':
        house_type = request.form.get('house_type', 'family')
        
        # Valider le type
        if house_type not in ['family', 'couple', 'coloc']:
            house_type = 'family'
        
        # Sauvegarder temporairement dans la session
        session['house_type'] = house_type
        house_name_input = request.form.get('house_name', '').strip()
        if house_name_input:
            session['house_name'] = house_name_input
        session['registration_step'] = 'house_type_chosen'
        
        # Rediriger vers l'étape 3 : invitation partenaires
        return redirect(url_for('onboarding_invite'))
    
    return render_template('choose_house_type.html')


@app.route('/onboarding_invite')
def onboarding_invite():
    """ÉTAPE 3 : Page d'explication + invitation partenaires"""
    if 'user' not in session:
        flash("Veuillez d'abord vous inscrire", "warning")
        return redirect(url_for('signup_email'))

    # En inscription, imposer le passage par l'étape "type de logement"
    if session.get('registration_step') == 'email_signup' and not session.get('house_type'):
        return redirect(url_for('choose_house_type'))
    
    # Récupérer ou créer le code de la maison
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    
    house_code = None
    house_id = None
    
    if row and row[0]:
        # L'utilisateur a déjà une maison
        house_id = row[0]
        c.execute("SELECT code FROM houses WHERE id=?", (house_id,))
        code_row = c.fetchone()
        if code_row and code_row[0]:
            house_code = code_row[0]
        else:
            # La maison existe mais n'a pas de code, on le génère
            import random
            import string
            house_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            c.execute("UPDATE houses SET code=? WHERE id=?", (house_code, house_id))
            conn.commit()
    else:
        # Créer une nouvelle maison avec un code
        import random
        import string
        house_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        c.execute("INSERT INTO houses (code, name, health, last_reset_date) VALUES (?, ?, ?, date('now'))", 
                 (house_code, '', 100))
        house_id = c.lastrowid
        c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, session['user']))
        conn.commit()
    
    conn.close()
    
    # Construire l'URL d'invitation (garantir que house_code n'est jamais None)
    if not house_code:
        house_code = "ERROR"
        join_url = ""
    else:
        join_url = f"{request.host_url}invite/{house_code}"
    
    return render_template('onboarding_invite.html', house_code=house_code, join_url=join_url)


@app.route('/name_house', methods=['GET', 'POST'])
def name_house():
    """ÉTAPE 4 : Nommer le foyer"""
    if 'user' not in session:
        flash("Veuillez d'abord vous inscrire", "warning")
        return redirect(url_for('signup_email'))
    
    if request.method == 'POST':
        house_name = request.form.get('house_name', '').strip()
        
        _dbg(f"🏠 NAME_HOUSE POST: house_name={house_name}, user={session.get('user')}")
        
        if not house_name:
            flash("Veuillez donner un nom à votre foyer", "danger")
            return render_template('name_house.html')
        
        # Sauvegarder dans la session
        session['house_name'] = house_name
        session['registration_step'] = 'house_named'
        
        _dbg(f"✅ NAME_HOUSE: Redirection vers create_profile")
        
        # Rediriger vers l'étape 5 : création du profil (avatar + pseudo)
        return redirect(url_for('create_profile'))
    
    _dbg(f"📄 NAME_HOUSE GET: Affichage du formulaire pour {session.get('user')}")
    return render_template('name_house.html')


# Route '/start' (quick signup) removed as requested. Use '/signup_email' instead.

@app.route('/quick_login', methods=['GET', 'POST'])
def quick_login():
    """Connexion rapide et joyeuse ! 🔑"""
    if request.method == 'GET':
        return render_template('quick_login.html')
        
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()
    
    if not email or not password:
        flash("🤔 Email et mot de passe requis !", "danger")
        return render_template('quick_login.html')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, password FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[1], password):
        session.permanent = True  # Session persistante après rafraîchissement
        session['user'] = email
        session['user_name'] = user[0]
        _log_login(email)
        flash(f"🎉 Re-bienvenue {user[0]} ! Prêt(e) pour de nouvelles aventures ? 🚀", "success")
        return redirect(url_for('menu'))
    else:
        flash("🚫 Email ou mot de passe incorrect ! Vérifie tes infos !", "danger")
        return render_template('quick_login.html')


# ========================================
# Routes pour la gestion des joueurs
# ========================================

@app.route('/manage_players')
def manage_players():
    """Page de gestion des joueurs de la maison"""
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur actuel
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_house = c.fetchone()
    
    if not user_house or not user_house[0]:
        conn.close()
        flash("Vous devez d'abord rejoindre une maison", "warning")
        return redirect(url_for('menu'))
    
    house_id = user_house[0]
    
    # Récupérer le nom de la maison
    c.execute("SELECT name FROM houses WHERE id=?", (house_id,))
    house_row = c.fetchone()
    house_name = house_row[0] if house_row else ""
    
    # Récupérer tous les joueurs de cette maison (inclut avatar_style pour DiceBear)
    c.execute("""
        SELECT email, name, avatar, avatar_file, avatar_url, player_color, avatar_style
        FROM users
        WHERE house_id=?
        ORDER BY name
    """, (house_id,))
    
    players = []
    for row in c.fetchall():
        email, name, avatar, avatar_file, avatar_url, player_color, avatar_style = row
        
        # Assigner une couleur si le joueur n'en a pas encore
        if not player_color:
            player_color = assign_player_color(email, house_id)
        
        # Convertir v8 → v7 et supprimer backgroundColor (fond coloré indésirable)
        import re as _re_mp
        if avatar_url and 'dicebear.com/8.x' in avatar_url:
            avatar_url = avatar_url.replace('dicebear.com/8.x', 'dicebear.com/7.x')
        if avatar_url and 'backgroundColor' in avatar_url:
            avatar_url = _re_mp.sub(r'[&?]backgroundColor=[^&]*', '', avatar_url).rstrip('?&')
        players.append({
            'email': email,
            'name': name,
            'avatar': avatar,
            'avatar_file': validate_avatar_file(avatar_file),
            'avatar_url': avatar_url,
            'avatar_style': avatar_style if avatar_style else 'adventurer',
            'color': player_color
        })
    
    conn.close()
    
    print(f'🏠 MANAGE_PLAYERS players={[(p["email"],p["name"],p["avatar"],p["avatar_url"]) for p in players]}', flush=True)
    return render_template('manage_players.html', 
                         players=players, 
                         house_name=house_name,
                         house_id=house_id,
                         hide_header=True)


@app.route('/edit_player/<path:email>')
def edit_player(email):
    """Page de modification d'un joueur"""
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Vérifier que l'utilisateur actuel et le joueur à modifier sont dans la même maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_house = c.fetchone()
    
    c.execute("SELECT house_id, email, name, avatar, avatar_file, avatar_url, avatar_style FROM users WHERE email=?", (email,))
    player_row = c.fetchone()
    
    if not user_house or not player_row or user_house[0] != player_row[0]:
        conn.close()
        flash("Non autorisé", "error")
        return redirect(url_for('manage_players'))
    
    # Supprimer backgroundColor des URLs DiceBear (fond coloré indésirable)
    import re as _re_ep
    ep_avatar_url = player_row[5]
    if ep_avatar_url and 'backgroundColor' in ep_avatar_url:
        ep_avatar_url = _re_ep.sub(r'[&?]backgroundColor=[^&]*', '', ep_avatar_url).rstrip('?&')
    player = {
        'email': player_row[1],
        'name': player_row[2],
        'avatar': player_row[3],
        'avatar_file': player_row[4],
        'avatar_url': ep_avatar_url,
        'avatar_style': player_row[6] if player_row[6] else 'adventurer'
    }
    
    conn.close()
    
    return render_template('edit_player.html', player=player, hide_header=True)


@app.route('/update_house_name', methods=['POST'])
def update_house_name():
    """Mettre à jour le nom de la maison"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'})
    
    try:
        new_name = request.form.get('house_name', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'error': 'Le nom ne peut pas être vide'})
        
        if len(new_name) > 50:
            return jsonify({'success': False, 'error': 'Le nom est trop long (max 50 caractères)'})
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer la maison de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        
        if not user_house or not user_house[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Aucune maison trouvée'})
        
        house_id = user_house[0]
        
        # Mettre à jour le nom de la maison (house_name a la priorité sur name)
        c.execute("UPDATE houses SET house_name=?, name=? WHERE id=?", (new_name, new_name, house_id))
        conn.commit()
        conn.close()
        _invalidate_house_cache(session['user'])  # ⚡ Invalider le cache du context_processor
        return jsonify({'success': True, 'message': 'Nom de la maison mis à jour !'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/update_player', methods=['POST'])
def update_player():
    """Mettre à jour le nom et l'avatar d'un joueur"""
    if 'user' not in session:
        _dbg("❌ UPDATE_PLAYER: Utilisateur non connecté")
        return jsonify({'success': False, 'error': 'Non connecté'})
    
    try:
        email = request.form.get('email')
        name = request.form.get('name', '').strip()
        avatar_type = request.form.get('avatar_type', '').strip()
        
        print("🔍 UPDATE_PLAYER - Données reçues:", flush=True)
        print(f"🔍 UPDATE_PLAYER email={email} name={name} avatar_type={avatar_type}", flush=True)
        _dbg(f"   name: {name}")
        _dbg(f"   avatar_type: '{avatar_type}'")
        _dbg(f"   avatar: {request.form.get('avatar')}")
        _dbg(f"   avatar_style: {request.form.get('avatar_style')}")
        _dbg(f"   session['user']: {session.get('user')}")
        _dbg(f"   Tous les champs: {dict(request.form)}")
        
        if not email:
            _dbg("❌ UPDATE_PLAYER: Email manquant")
            return jsonify({'success': False, 'error': 'Email requis'})
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Vérifier que l'utilisateur actuel et le joueur à modifier sont dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        
        c.execute("SELECT house_id FROM users WHERE email=?", (email,))
        player_house = c.fetchone()
        
        _dbg(f"   user_house: {user_house}")
        _dbg(f"   player_house: {player_house}")
        
        if not user_house or not player_house:
            conn.close()
            _dbg("❌ UPDATE_PLAYER: Utilisateur ou joueur non trouvé")
            return jsonify({'success': False, 'error': 'Utilisateur ou joueur non trouvé'})
            
        if user_house[0] != player_house[0]:
            conn.close()
            _dbg("❌ UPDATE_PLAYER: Maisons différentes, non autorisé")
            return jsonify({'success': False, 'error': 'Non autorisé - vous devez être dans la même maison'})
        
        # 📛 Récupérer l'ancien nom AVANT la mise à jour (pour propager le changement)
        c.execute("SELECT name FROM users WHERE email=?", (email,))
        old_name_row = c.fetchone()
        old_name = old_name_row[0] if old_name_row and old_name_row[0] else None
        
        # Préparer la mise à jour
        update_parts = []
        update_values = []
        
        if name:
            update_parts.append("name=?")
            update_values.append(name)
            _dbg(f"   ✅ Ajout du nom à la mise à jour: '{name}'")
        
        # Gérer l'avatar SEULEMENT si avatar_type est fourni et valide
        if avatar_type == 'emoji':
            emoji = request.form.get('avatar', '').strip() or request.form.get('avatar_emoji', '').strip()
            if emoji:
                # Valider que c'est bien un emoji (max 4 caractères, Unicode > 127)
                if len(emoji) <= 4 and any(ord(ch) > 127 for ch in emoji):
                    update_parts.append("avatar=?")
                    update_values.append(emoji)
                    # Effacer les autres types d'avatar
                    update_parts.append("avatar_file=?")
                    update_values.append(None)
                    update_parts.append("avatar_url=?")
                    update_values.append(None)
                    _dbg(f"   ✅ Avatar emoji: {emoji}")
        
        elif avatar_type == 'dicebear':
            # Avatar DiceBear : récupérer le seed et construire l'URL
            seed = request.form.get('avatar', '').strip()
            style = request.form.get('avatar_style', 'avataaars').strip()
            _dbg(f"✅ Avatar DiceBear détecté - seed: {seed}, style: {style}")
            if seed:
                dicebear_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={seed}"
                update_parts.append("avatar_url=?")
                update_values.append(dicebear_url)
                # Stocker le seed dans avatar pour le retrouver
                update_parts.append("avatar=?")
                update_values.append(seed)
                # Stocker le style
                update_parts.append("avatar_style=?")
                update_values.append(style)
                # Effacer avatar_file
                update_parts.append("avatar_file=?")
                update_values.append(None)
                _dbg(f"   URL construite: {dicebear_url}")
                _dbg(f"   Champs à mettre à jour: avatar={seed}, avatar_style={style}, avatar_url={dicebear_url}")
        
        elif avatar_type == 'file':
            # Sélection d'une image PNG existante depuis la galerie
            avatar_filename = request.form.get('avatar', '').strip()
            _dbg(f"   Avatar file détecté: {avatar_filename}")
            if avatar_filename and avatar_filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                update_parts.append("avatar_file=?")
                update_values.append(avatar_filename)
                # Effacer les autres types d'avatar
                update_parts.append("avatar=?")
                update_values.append(None)
                update_parts.append("avatar_url=?")
                update_values.append(None)
                _dbg(f"   ✅ Avatar file conservé: {avatar_filename}")
        
        elif avatar_type == 'photo':
            # Gérer l'upload de fichier → data URI en DB (compatible Render)
            if 'avatar_file' in request.files:
                file = request.files['avatar_file']
                if file and file.filename:
                    raw_data = file.read()
                    try:
                        from PIL import Image
                        import io as _io_p
                        img = Image.open(_io_p.BytesIO(raw_data)).convert('RGB')
                        img.thumbnail((400, 400), Image.LANCZOS)
                        buf = _io_p.BytesIO()
                        img.save(buf, format='JPEG', quality=75, optimize=True)
                        raw_data = buf.getvalue()
                    except ImportError:
                        pass
                    data_uri = "data:image/jpeg;base64," + base64.b64encode(raw_data).decode('utf-8')
                    update_parts.append("avatar_url=?")
                    update_values.append(data_uri)
                    # Effacer les autres types d'avatar
                    update_parts.append("avatar=?")
                    update_values.append(None)
                    update_parts.append("avatar_file=?")
                    update_values.append(None)
                    _dbg(f"   ✅ Photo stockée en DB (data URI, {len(data_uri)} chars)")
        else:
            # Si avatar_type est vide ou inconnu, ne pas toucher à l'avatar
            _dbg(f"   ℹ️ Avatar type vide ou inconnu ('{avatar_type}'), conservation de l'avatar actuel")
        
        print(f"📋 update_parts={update_parts}, avatar_type={avatar_type}, seed={request.form.get(chr(97)+chr(118)+chr(97)+chr(116)+chr(97)+chr(114))}", flush=True)
        if update_parts:
            update_values.append(email)
            query = f"UPDATE users SET {', '.join(update_parts)} WHERE email=?"
            _dbg(f"   📝 Requête SQL: {query}")
            _dbg(f"   📝 Valeurs: {update_values}")
            c.execute(query, update_values)
            print(f"✅ UPDATE_PLAYER SQL OK rowcount={c.rowcount}", flush=True)
            
            conn.commit()
            print("✅ COMMIT OK", flush=True)
            
            # 📛 Propager le changement de nom dans les messages existants
            if name and old_name and name != old_name:
                house_id = user_house[0]
                try:
                    propagate_player_name_change(c, email, old_name, name, house_id)
                    conn.commit()
                except Exception as prop_err:
                    print(f"⚠️ propagate ignoré: {prop_err}", flush=True)
                _dbg(f"📛 Nom du joueur changé: '{old_name}' → '{name}' pour {email}")
                
                # Mettre à jour la session si c'est l'utilisateur connecté
                if email == session.get('user'):
                    session['user_name'] = name
                    if 'name' in session:
                        session['name'] = name
            
            # 🔌 WEBSOCKET: Notifier tous les joueurs du changement
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    house_id = user_house[0]
                    # Récupérer les données fraîches après commit pour diffuser l'avatar réel
                    c.execute("SELECT name, avatar, avatar_url, avatar_file FROM users WHERE email=?", (email,))
                    fresh = c.fetchone()
                    if fresh:
                        player_data = {
                            'email': email,
                            'name': fresh[0],
                            'avatar': fresh[1],
                            'avatar_url': fresh[2],
                            'avatar_file': fresh[3]
                        }
                        socketio.emit('player_avatar_update', player_data, namespace='/', to=f'house_{house_id}')
                    # Si le nom a changé, notifier aussi pour rafraîchir les affichages
                    if name and old_name and name != old_name:
                        socketio.emit('player_name_updated', {
                            'email': email, 
                            'old_name': old_name, 
                            'new_name': name
                        }, namespace='/', to=f'house_{house_id}')
                    _dbg(f"🔌 WebSocket: Diffusion changement pour {email} (room: house_{house_id})")
                except Exception as ws_err:
                    print(f"⚠️ Erreur WebSocket: {ws_err}", flush=True)
        else:
            _dbg("   ⚠️ Aucune modification à effectuer (update_parts vide)")
        
        conn.close()
        
        print("✅✅✅ UPDATE_PLAYER terminé avec succès", flush=True)
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"❌❌❌ [ERROR update_player] {e}", flush=True)
        import traceback
        _dbg(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})


@app.route('/delete_player', methods=['POST'])
def delete_player():
    """Supprimer un joueur de la maison (mettre house_id à NULL)"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'})
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email requis'})
        
        # Empêcher l'utilisateur de se supprimer lui-même
        if email == session['user']:
            return jsonify({'success': False, 'error': 'Vous ne pouvez pas vous supprimer vous-même'})
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Vérifier que l'utilisateur actuel et le joueur à supprimer sont dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        
        c.execute("SELECT house_id FROM users WHERE email=?", (email,))
        player_house = c.fetchone()
        
        if not user_house or not player_house or user_house[0] != player_house[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        house_id = user_house[0]
        
        # Récupérer le nom du joueur avant suppression
        c.execute("SELECT name FROM users WHERE email=?", (email,))
        player_row = c.fetchone()
        player_name = player_row[0] if player_row and player_row[0] else email.split('@')[0]
        
        # Supprimer le joueur de la maison (mettre house_id à NULL)
        c.execute("UPDATE users SET house_id=NULL WHERE email=?", (email,))
        conn.commit()
        
        # Récupérer la liste mise à jour des joueurs
        c.execute("""
            SELECT email, name, avatar, avatar_file, avatar_url, avatar_style, points, player_color 
            FROM users 
            WHERE house_id = ?
            ORDER BY name
        """, (house_id,))
        
        players = c.fetchall()
        players_data = []
        for p in players:
            email_p, name_p, avatar_p, avatar_file_p, avatar_url_p, avatar_style_p, points_p, player_color_p = p
            
            # Gérer l'URL de l'avatar
            clean_avatar_url = None
            valid_file_p = validate_avatar_file(avatar_file_p)
            if valid_file_p:
                clean_avatar_url = f"/static/avatars/{valid_file_p}"
            elif avatar_url_p:
                clean_avatar_url = avatar_url_p
            elif avatar_p:
                # Si c'est un seed DiceBear (8 caractères alphanumériques)
                if len(avatar_p) == 8 and avatar_p.isalnum():
                    style = avatar_style_p if avatar_style_p else 'lorelei'
                    clean_avatar_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={avatar_p}"
                else:
                    clean_avatar_url = avatar_p
            
            players_data.append({
                'email': email_p,
                'name': name_p or email_p.split('@')[0],
                'avatar_url': clean_avatar_url,
                'points': points_p or 0,
                'player_color': player_color_p
            })
        
        conn.close()
        
        # Émettre l'événement WebSocket
        _dbg(f"🔌 WebSocket: Joueur '{player_name}' supprimé (room: house_{house_id})")
        socketio.emit('players_list_update', {
            'players': players_data,
            'deleted_player': player_name,
            'action': 'player_deleted'
        }, namespace='/', room=f'house_{house_id}')
        
        return jsonify({'success': True})
        
    except Exception as e:
        _dbg(f"[ERROR delete_player] {e}")
        return jsonify({'success': False, 'error': str(e)})


# ========================================
# Routes pour ajouter des joueurs
# ========================================

@app.route('/add_players')
def add_players():
    """Page de choix : ajouter enfants ou inviter partenaires"""
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    # Récupérer les joueurs de la maison pour afficher le header
    players = []
    current_user_name = session.get('user', '')
    player1_name = None
    player1_avatar = None
    player1_avatar_url = None
    current_user_daily_points = 0
    house_health = 100
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    
    if row and row[0]:
        house_id = row[0]
        players = get_house_players_points(house_id)
        
        # Récupérer les infos du joueur actuel
        c.execute("SELECT name, avatar, avatar_file, avatar_url FROM users WHERE email=?", (session['user'],))
        user_row = c.fetchone()
        if user_row:
            player1_name = user_row[0] or session['user'].split('@')[0]
            player1_avatar = user_row[1]
            avatar_file = user_row[2]
            player1_avatar_url = user_row[3]
            valid_file = validate_avatar_file(avatar_file)
            if valid_file:
                player1_avatar_url = url_for('static', filename='avatars/' + valid_file)
        
        # Points du jour pour le joueur actuel
        from datetime import date
        today = date.today().isoformat()
        c.execute("SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at)=?", (session['user'], today))
        pts = c.fetchone()
        current_user_daily_points = int(pts[0]) if pts and pts[0] else 0
        
        # Ajouter les points du jour à chaque joueur
        for p in players:
            email = p.get('email')
            if email:
                c.execute("SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at)=?", (email, today))
                sums = c.fetchone()
                p['daily_points'] = int(sums[0]) if sums and sums[0] else 0
        
        # Santé de la maison
        try:
            c.execute("SELECT health FROM houses WHERE id=?", (house_id,))
            hrow = c.fetchone()
            house_health = hrow[0] if hrow and hrow[0] is not None else 100
        except:
            house_health = 100
    
    conn.close()
    
    return render_template('add_players.html',
                           players=players,
                           current_user_name=current_user_name,
                           player1_name=player1_name,
                           player1_avatar=player1_avatar,
                           player1_avatar_url=player1_avatar_url,
                           current_user_daily_points=current_user_daily_points,
                           house_health=house_health,
                           hide_header=True)


@app.route('/add_children')
def add_children():
    """Page pour ajouter des enfants (sans téléphone)"""
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    return render_template('add_children.html')


@app.route('/add_child', methods=['POST'])
def add_child():
    """Créer un profil enfant sans email ni mot de passe"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'})
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer la maison du parent
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        parent = c.fetchone()
        
        if not parent or not parent[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Vous devez avoir une maison'})
        
        house_id = parent[0]
        child_name = request.form.get('child_name', '').strip().capitalize()
        
        if not child_name:
            conn.close()
            return jsonify({'success': False, 'error': 'Le prénom est requis'})
        
        # Gérer l'avatar
        avatar = None
        avatar_file = None
        avatar_url = None
        
        # Vérifier si c'est un avatar DiceBear, un emoji ou une photo
        child_avatar = request.form.get('child_avatar', '').strip()
        child_avatar_style = request.form.get('child_avatar_style', '').strip()
        child_photo = request.files.get('child_photo')
        
        if child_avatar and child_avatar_style:
            # Avatar DiceBear : seed de 8 caractères + style
            if len(child_avatar) == 8 and child_avatar_style:
                avatar_url = f"https://api.dicebear.com/7.x/{child_avatar_style}/svg?seed={child_avatar}"
                avatar = child_avatar  # Stocker le seed
                _dbg(f"✅ [ADD_CHILD] Avatar DiceBear: {avatar_url}")
        elif child_avatar and len(child_avatar) <= 4 and any(ord(c) > 127 for c in child_avatar):
            # Emoji (legacy)
            avatar = child_avatar
        elif child_photo and child_photo.filename:
            # Sauvegarder la photo
            filename = secure_filename(child_photo.filename)
            unique_filename = f"child_{int(time.time())}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            child_photo.save(filepath)
            avatar_file = unique_filename
        else:
            # Avatar par défaut DiceBear
            default_seed = 'baby' + str(int(time.time()))[-4:]
            child_avatar_style = 'avataaars'  # Style par défaut pour les enfants
            avatar_url = f"https://api.dicebear.com/7.x/{child_avatar_style}/svg?seed={default_seed}"
            avatar = default_seed[:8]
        
        # Créer un email unique pour l'enfant (interne, pas utilisé pour connexion)
        child_email = f"child_{house_id}_{int(time.time())}@cleanbeat.internal"
        
        # Insérer l'enfant dans la base avec le style d'avatar ET le flag is_child_account
        c.execute("""
            INSERT INTO users (email, name, avatar, avatar_file, avatar_url, avatar_style, house_id, password, is_child_account)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 1)
        """, (child_email, child_name, avatar, avatar_file, avatar_url, child_avatar_style or None, house_id))
        
        conn.commit()
        
        # 🔌 Récupérer tous les joueurs de la maison pour WebSocket (y compris les enfants)
        c.execute("""
            SELECT email, name, avatar, avatar_file, avatar_url, avatar_style, points, player_color
            FROM users 
            WHERE house_id = ?
            ORDER BY name
        """, (house_id,))
        
        players_data = []
        for player in c.fetchall():
            player_email, player_name, player_avatar, player_avatar_file, player_avatar_url, player_avatar_style, player_points, player_color = player
            
            # Déterminer l'URL de l'avatar
            display_avatar_url = None
            if player_avatar_url:
                display_avatar_url = player_avatar_url
            elif validate_avatar_file(player_avatar_file):
                display_avatar_url = f"/static/avatars/{player_avatar_file}"
            elif player_avatar and player_avatar_style:
                display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style}/svg?seed={player_avatar}"
            else:
                display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style or 'adventurer'}/svg?seed={player_name or player_email}"
            
            players_data.append({
                'email': player_email,
                'name': player_name,
                'avatar_url': display_avatar_url,
                'points': player_points or 0,
                'color': player_color
            })
        
        conn.close()
        
        # 🔌 Émettre WebSocket pour synchroniser tous les écrans
        try:
            socketio.emit('players_list_update', {
                'players': players_data,
                'new_player': child_name,
                'action': 'child_added'
            }, namespace='/', room=f'house_{house_id}')
            _dbg(f"🔌 WebSocket: Enfant '{child_name}' ajouté (room: house_{house_id})")
        except Exception as ws_err:
            _dbg(f"⚠️ Erreur WebSocket ajout enfant: {ws_err}")
        
        return jsonify({'success': True, 'message': 'Enfant ajouté'})
        
    except Exception as e:
        _dbg(f"[ERROR add_child] {e}")
        return jsonify({'success': False, 'error': str(e)})


# ========================================
# Routes pour les rappels personnels (mini agenda / to-do list)
# ========================================

@app.route('/reminders')
def reminders():
    """Page des rappels personnels du joueur (mini agenda)"""
    if 'user' not in session:
        flash("Connecte-toi pour accéder à tes rappels", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    if not row or not row[0]:
        conn.close()
        flash("Tu dois d'abord rejoindre une maison", "warning")
        return redirect(url_for('menu'))

    house_id, player_name = row[0], row[1]

    # Marquer comme lus les messages courses_added à chaque visite
    try:
        c.execute("""
            SELECT m.id FROM messages m
            WHERE m.house_id = ? AND m.message_type = 'courses_added'
            AND NOT EXISTS (SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?)
        """, (house_id, session['user']))
        for msg_row in c.fetchall():
            mark_message_as_read(msg_row[0], session['user'])
    except Exception as e:
        _dbg(f"⚠️ Erreur marquage courses_added: {e}")

    # Liste partagée par toute la maison (visible par tous les joueurs)
    c.execute("""
        SELECT pr.id, pr.title, pr.remind_at, pr.is_done, pr.created_at, pr.user_email, 
               u.name, u.avatar, u.avatar_file, u.avatar_url
        FROM player_reminders pr
        LEFT JOIN users u ON pr.user_email = u.email
        WHERE pr.house_id=?
        ORDER BY pr.is_done ASC, CASE WHEN pr.remind_at IS NULL THEN 1 ELSE 0 END, pr.remind_at ASC, pr.created_at ASC
    """, (house_id,))
    reminders_rows = c.fetchall()
    conn.close()

    reminders_list = [
        {
            'id': r[0], 
            'title': r[1], 
            'remind_at': r[2], 
            'is_done': bool(r[3]), 
            'created_at': r[4],
            'user_email': r[5],
            'creator_name': r[6] if r[6] else (r[5].split('@')[0] if r[5] else 'Inconnu'),
            'creator_avatar': r[7],
            'creator_avatar_file': r[8],
            'creator_avatar_url': r[9]
        }
        for r in reminders_rows
    ]

    active_reminders = [r for r in reminders_list if not r['is_done']]
    done_reminders   = [r for r in reminders_list if r['is_done']]

    return render_template('reminders.html',
                           reminders=reminders_list,
                           active_reminders=active_reminders,
                           done_reminders=done_reminders,
                           hide_header=True)


@app.route('/reminders/add', methods=['POST'])
def add_reminder():
    """Ajouter un rappel personnel"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    title = request.form.get('title', '').strip()
    remind_at = request.form.get('remind_at', '').strip() or None

    if not title:
        return jsonify({'success': False, 'error': 'Titre requis'})

    # Valider le format remind_at HH:MM
    if remind_at:
        import re as _re_r
        if not _re_r.match(r'^\d{2}:\d{2}$', remind_at):
            remind_at = None

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_row = c.fetchone()
    if not house_row or not house_row[0]:
        conn.close()
        return jsonify({'success': False, 'error': 'Maison introuvable'})

    house_id = house_row[0]
    c.execute("""
        INSERT INTO player_reminders (user_email, house_id, title, remind_at)
        VALUES (?, ?, ?, ?)
    """, (session['user'], house_id, title, remind_at))
    new_id = c.lastrowid
    conn.commit()

    # 🛒 Nombre d'articles en attente après l'ajout (pour badge nav)
    _courses_pending = 0
    try:
        c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (house_id,))
        _courses_pending = c.fetchone()[0] or 0
    except Exception:
        pass

    # 🛒 Créer un message automatique pour notifier l'ajout à la liste de courses
    creator_name = ''
    creator_avatar = ''
    creator_avatar_file = ''
    creator_avatar_url = ''
    try:
        c.execute("SELECT name, avatar, avatar_file, avatar_url FROM users WHERE email=?", (session['user'],))
        creator_row = c.fetchone()
        if creator_row:
            creator_name = creator_row[0] if creator_row[0] else session['user'].split('@')[0]
            creator_avatar = creator_row[1]
            creator_avatar_file = creator_row[2]
            creator_avatar_url = creator_row[3]
        else:
            creator_name = session['user'].split('@')[0]
        message_content = f"🛒 {creator_name} a ajouté \"{title}\" à la liste de courses"
        create_system_message(house_id, message_content, 'courses_added', sender_email=session['user'])
    except Exception:
        if not creator_name:
            creator_name = session['user'].split('@')[0]

    # Synchroniser l'ajout pour tous les joueurs de la maison
    try:
        safe_socketio_emit('reminder_added', {
            'id': new_id,
            'title': title,
            'pending_count': _courses_pending
        }, namespace='/', room=f'house_{house_id}', broadcast=True)
    except Exception:
        pass

    conn.close()

    return jsonify({
        'success': True, 
        'id': new_id, 
        'title': title, 
        'remind_at': remind_at,
        'creator_name': creator_name,
        'creator_avatar': creator_avatar,
        'creator_avatar_file': creator_avatar_file,
        'creator_avatar_url': creator_avatar_url
    })


@app.route('/reminders/toggle/<int:reminder_id>', methods=['POST'])
def toggle_reminder(reminder_id):
    """Cocher / décocher un article de la liste de courses (+1 pt quand on coche)"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    conn = get_db_connection()
    c = conn.cursor()
    # Vérifier que l'article appartient à la même maison que le joueur connecté
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'error': 'Maison introuvable'})
    user_house = user_row[0]
    c.execute("SELECT is_done FROM player_reminders WHERE id=? AND house_id=?",
              (reminder_id, user_house))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Article introuvable'})

    new_done = 0 if row[0] else 1
    c.execute("UPDATE player_reminders SET is_done=? WHERE id=?", (new_done, reminder_id))

    # +1 point quand on coche un article (au joueur connecté, pas au créateur)
    points_earned = 0
    new_total_points = 0
    house_id = user_house
    if new_done == 1:
        c.execute("SELECT points FROM users WHERE email=?", (session['user'],))
        pts_row = c.fetchone()
        if pts_row:
            current_pts = pts_row[0] or 0
            new_total_points = current_pts + 1
            c.execute("UPDATE users SET points=? WHERE email=?", (new_total_points, session['user']))
            # Insérer dans completed_tasks pour que daily_points du header soit correct
            c.execute("INSERT INTO completed_tasks (user_email, house_id, category, task_name, points, completed_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                      (session['user'], house_id, 'courses', 'Liste de courses', 1))
            points_earned = 1

    conn.commit()

    # Si l'article vient d'être coché, vérifier si TOUTE la liste est faite
    # → marquer tous les courses_added non lus comme lus pour cet utilisateur
    if new_done == 1:
        try:
            conn_check = get_db_connection()
            c_check = conn_check.cursor()
            c_check.execute(
                "SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0",
                (user_house,)
            )
            remaining = c_check.fetchone()[0]
            if remaining == 0:
                # Toute la liste est cochée → éteindre la pill courses pour cet utilisateur
                c_check.execute("""
                    SELECT m.id FROM messages m
                    WHERE m.house_id = ? AND m.message_type = 'courses_added'
                    AND NOT EXISTS (
                        SELECT 1 FROM message_reads mr
                        WHERE mr.message_id = m.id AND mr.user_email = ?
                    )
                """, (user_house, session['user']))
                for msg_row in c_check.fetchall():
                    c_check.execute("""
                        INSERT INTO message_reads (message_id, user_email)
                        VALUES (?, ?) ON CONFLICT(message_id, user_email) DO NOTHING
                    """, (msg_row[0], session['user']))
                conn_check.commit()
            conn_check.close()
        except Exception:
            pass

    # Diffuser la mise à jour des points via WebSocket
    if points_earned > 0:
        try:
            c.execute("""
                SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
                       COALESCE(SUM(ct.points), 0) as daily_points
                FROM users u
                LEFT JOIN completed_tasks ct ON u.email = ct.user_email
                    AND DATE(ct.completed_at) = DATE('now')
                WHERE u.house_id = ?
                GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.points
                ORDER BY daily_points DESC, u.points DESC
            """, (house_id,))
            players_ws = [{'email': p[0], 'name': p[1], 'avatar': p[2], 'avatar_url': p[3],
                           'avatar_file': p[4], 'total_points': p[5] or 0,
                           'daily_points': int(p[6]) if p[6] else 0} for p in c.fetchall()]
            safe_socketio_emit('players_points_update', {
                'players': players_ws, 'updated_player': session['user']
            }, namespace='/', room=f'house_{house_id}', broadcast=True)
        except Exception as ws_err:
            _dbg(f"⚠️ WebSocket liste courses: {ws_err}")

    # 🛒 Nombre d'articles non cochés après le toggle (pour badge nav)
    _courses_after = 0
    try:
        c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (user_house,))
        _courses_after = c.fetchone()[0] or 0
    except Exception:
        pass

    # Diffuser le toggle à tous les autres membres de la maison (synchro liste)
    try:
        safe_socketio_emit('reminder_toggle', {
            'id': reminder_id,
            'is_done': bool(new_done),
            'pending_count': _courses_after
        }, namespace='/', room=f'house_{house_id}', broadcast=True)
    except Exception:
        pass

    # Récupérer nom du joueur pour l'animation avatar côté menu
    player_name_resp = ''
    try:
        conn2 = get_db_connection()
        pn = conn2.execute("SELECT name FROM users WHERE email=?", (session['user'],)).fetchone()
        player_name_resp = pn[0] if pn else session['user'].split('@')[0]
        conn2.close()
    except Exception:
        player_name_resp = session['user'].split('@')[0]

    conn.close()

    return jsonify({
        'success': True,
        'is_done': bool(new_done),
        'points_earned': points_earned,
        'new_total_points': new_total_points,
        'player_email': session['user'],
        'player_name': player_name_resp
    })


@app.route('/reminders/delete/<int:reminder_id>', methods=['POST'])
def delete_reminder(reminder_id):
    """Supprimer un rappel"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    conn = get_db_connection()
    c = conn.cursor()
    # Permettre à n'importe quel membre de la maison de supprimer
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    hr = c.fetchone()
    if hr and hr[0]:
        c.execute("DELETE FROM player_reminders WHERE id=? AND house_id=?",
                  (reminder_id, hr[0]))
    conn.commit()
    conn.close()

    # Synchroniser la suppression pour tous les joueurs
    if hr and hr[0]:
        try:
            safe_socketio_emit('reminder_deleted', {
                'id': reminder_id
            }, namespace='/', room=f'house_{hr[0]}', broadcast=True)
        except Exception:
            pass

    return jsonify({'success': True})


@app.route('/comments', methods=['GET','POST'])
def comments():
    """
    Messagerie améliorée avec:
    - Messages entre joueurs de la maison
    - Messages automatiques (tâches validées/ajoutées)
    - Système de lu/non-lu
    - Badge de notification
    """
    try:
        return _comments_inner()
    except Exception as _e:
        import traceback
        print(f'❌ ERREUR /comments: {_e}', flush=True)
        traceback.print_exc()
        raise

def _comments_inner():
    if 'user' not in session:
        flash("Connecte-toi pour accéder à la messagerie", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        flash("Tu dois rejoindre une maison pour accéder à la messagerie", "warning")
        return redirect(url_for('menu'))
    
    house_id = user_row[0]
    current_user_name = user_row[1] if user_row[1] else session['user'].split('@')[0]

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        recipient_email = request.form.get('recipient', '').strip()
        
        if content and recipient_email:
            # Vérifier que le destinataire existe dans la même maison
            c.execute("""
                SELECT email, name 
                FROM users 
                WHERE email = ? AND house_id = ?
            """, (recipient_email, house_id))
            recipient = c.fetchone()
            
            if recipient:
                # Créer un message privé
                c.execute("""
                    INSERT INTO messages (house_id, sender_email, recipient_email, sender_type, content, message_type)
                    VALUES (?, ?, ?, 'user', ?, 'private')
                """, (house_id, session['user'], recipient_email, content))
                conn.commit()
                
                # IMPORTANT : Récupérer l'ID du message qui vient d'être créé
                message_id = c.lastrowid
                
                # ✅ CORRECTION : Marquer automatiquement le message comme "lu" pour l'EXPÉDITEUR
                # Un joueur qui envoie un message ne doit jamais voir son propre message comme "non lu"
                mark_message_as_read(message_id, session['user'])
                _dbg(f"✅ Message ID {message_id} automatiquement marqué comme lu pour l'expéditeur {session['user']}")
                
                # Vérifier si le destinataire est un enfant (sans téléphone)
                c.execute("SELECT is_child_account FROM users WHERE email = ?", (recipient_email,))
                recipient_data = c.fetchone()
                is_recipient_child = recipient_data and recipient_data[0] == 1
                
                # ✅ Compteurs simplifiés
                recipient_unread_count = get_unread_message_count(recipient_email, house_id)
                children_unread = get_children_unread_counts(house_id)
                
                _dbg(f"📊 Message envoyé de {session['user']} à {recipient_email}")
                _dbg(f"👶 Destinataire est enfant: {is_recipient_child}")
                _dbg(f"📊 Compteur DESTINATAIRE {recipient_email} après envoi: {recipient_unread_count}")
                _dbg(f"🎯 Données à envoyer via WebSocket:")
                _dbg(f"   - sender: {current_user_name}")
                _dbg(f"   - sender_email: {session['user']}")
                _dbg(f"   - recipient_email: {recipient_email}")
                _dbg(f"   - recipient_is_child: {is_recipient_child}")
                _dbg(f"   - recipient_unread_count: {recipient_unread_count}")
                _dbg(f"   - children_unread: {children_unread}")
                
                # ✅ Émettre l'événement WebSocket SIMPLIFIÉ avec protection contre sessions invalides
                safe_socketio_emit('new_message_notification', {
                    'sender': current_user_name,
                    'sender_email': session['user'],
                    'content': content[:50] + ('...' if len(content) > 50 else ''),
                    'recipient_email': recipient_email,
                    'recipient_is_child': is_recipient_child,
                    'recipient_unread_count': recipient_unread_count,
                    'children_unread': children_unread
                }, namespace='/', room=f'house_{house_id}', broadcast=True)
                _dbg(f"✅ WebSocket new_message_notification émis vers house_{house_id}")
                
                # 🔌 Synchroniser la liste des messages pour tous les utilisateurs
                safe_socketio_emit('messages_list_update', {
                    'house_id': house_id,
                    'action': 'new_message',
                    'sender_email': session['user'],
                    'recipient_email': recipient_email
                }, namespace='/', room=f'house_{house_id}', broadcast=True)
                _dbg(f"✅ WebSocket messages_list_update émis vers house_{house_id}")
                
                # 🔔 Envoyer une notification push au destinataire
                try:
                    subscriptions = get_user_push_subscriptions(recipient_email)
                    if subscriptions:
                        notification_data = {
                            'title': f'💬 Message de {current_user_name}',
                            'body': content[:100] + ('...' if len(content) > 100 else ''),
                            'icon': '/static/images/logo.png',
                            'url': '/menu',
                            'badge': recipient_unread_count
                        }
                        for sub in subscriptions:
                            send_push_notification(sub, notification_data)
                        _dbg(f"🔔 Notification push envoyée à {recipient_email}")
                except Exception as e:
                    _dbg(f"⚠️ Erreur envoi notification push: {e}")
                
                # Pas de flash() ici → évite double notification (flash sur /comments + flash sur /menu)
                # La confirmation est faite via ?sent=1 (toast JS local, sans session flash)
                recipient_name = recipient[1] if recipient[1] else recipient[0]
                return redirect(url_for('comments') + f'?sent=1&to={recipient_name}')
            else:
                flash("Destinataire invalide.", "danger")
        else:
            flash("Veuillez sélectionner un destinataire et écrire un message.", "danger")
        
        return redirect(url_for('comments'))

    # Récupérer le code et le nom de la maison AVANT d'afficher les messages
    c.execute("SELECT code, name FROM houses WHERE id=?", (house_id,))
    house_row = c.fetchone()
    house_code = house_row[0] if house_row else None
    house_name = house_row[1] if house_row and house_row[1] else 'Ma Maison'

    # ✅ Récupérer UNIQUEMENT les messages privés où l'utilisateur est impliqué (envoyeur OU destinataire)
    # Logique simplifiée : chaque utilisateur ne voit QUE ses propres conversations
    _dbg(f"🔍 /comments - Récupération messages pour house_id={house_id}, user={session['user']}")
    
    c.execute("""
        SELECT m.id, m.sender_email, m.recipient_email, m.content, m.timestamp, m.sender_type, m.message_type,
               sender.name, sender.avatar, sender.avatar_file, sender.avatar_url, sender.avatar_style,
               recipient.name, recipient.avatar, recipient.avatar_file, recipient.avatar_url, recipient.avatar_style,
               CASE WHEN EXISTS (
                   SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = m.recipient_email
               ) THEN 1 ELSE 0 END as is_read_by_recipient,
               CASE WHEN EXISTS (
                   SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?
               ) THEN 1 ELSE 0 END as is_read_by_me,
               COALESCE(recipient.is_child_account, 0) as recipient_is_child
        FROM messages m
        LEFT JOIN users sender ON m.sender_email = sender.email
        LEFT JOIN users recipient ON m.recipient_email = recipient.email
        WHERE m.house_id = ?
        AND m.message_type = 'private'
        AND (m.sender_email = ? OR m.recipient_email = ?)
        ORDER BY m.id DESC
        LIMIT 100
    """, (session['user'], house_id, session['user'], session['user']))
    
    
    all_rows = c.fetchall()
    _dbg(f"🔍 /comments - Nombre de messages récupérés: {len(all_rows)}")
    
    # DEBUG: Afficher les 5 premiers messages avec leur ID, timestamp et type
    _dbg(f"🔍 DEBUG - Ordre des 5 premiers messages:")
    for i, row in enumerate(all_rows[:5]):
        msg_id, sender_email, _, content, timestamp, sender_type, message_type = row[:7]
        _dbg(f"  {i+1}. ID={msg_id}, timestamp={timestamp}, type={message_type}, sender_type={sender_type}")
        _dbg(f"     content={content[:40]}...")
    
    messages_data = []
    for row in all_rows:
        msg_id, sender_email, recipient_email, content, timestamp, sender_type, message_type, sender_name, sender_avatar, sender_avatar_file, sender_avatar_url, sender_avatar_style, recipient_name, recipient_avatar, recipient_avatar_file, recipient_avatar_url, recipient_avatar_style, is_read_by_recipient, is_read_by_me, recipient_is_child = row
        
        # Préparer l'avatar et nom de l'expéditeur
        if sender_type == 'house':
            # Pour les messages baby_tracking, sender_email contient l'email du joueur
            if message_type == 'baby_tracking':
                # Utiliser les infos du joueur (sender) - CORRIGER l'affichage
                display_sender_avatar = None
                if validate_avatar_file(sender_avatar_file):
                    display_sender_avatar = f"/static/avatars/{sender_avatar_file}"
                elif sender_avatar_url:
                    display_sender_avatar = sender_avatar_url
                elif sender_avatar and len(str(sender_avatar)) <= 4:
                    # C'est un emoji
                    display_sender_avatar = sender_avatar
                elif sender_avatar:  # Avatar DiceBear seed
                    # Récupérer le style stocké au lieu d'utiliser 'lorelei' par défaut
                    sender_style = sender_avatar_style if sender_avatar_style else 'adventurer'  # Style par défaut plus sympa
                    display_sender_avatar = f"https://api.dicebear.com/7.x/{sender_style}/svg?seed={sender_avatar}&backgroundColor=transparent"
                    _dbg(f"🍼 DEBUG: Avatar baby_tracking pour {sender_email}: seed={sender_avatar}, style={sender_style}")
                else:
                    display_sender_avatar = '👤'
                
                # S'assurer d'avoir le nom du joueur
                if not sender_name or sender_name.strip() == '':
                    sender_name = sender_email.split('@')[0] if sender_email else 'Inconnu'
                    if 'child_' in sender_email:
                        # Pour les enfants, essayer de récupérer le vrai nom
                        try:
                            temp_conn = get_db_connection()
                            temp_c = temp_conn.cursor()
                            temp_c.execute("SELECT name FROM users WHERE email=?", (sender_email,))
                            temp_row = temp_c.fetchone()
                            if temp_row and temp_row[0]:
                                sender_name = temp_row[0]
                            temp_conn.close()
                        except:
                            pass
            else:
                # Message de la maison classique - utiliser l'avatar maison
                display_sender_avatar = '🏠'
                # sender_email contient le nom de la maison pour les messages 'house'
                sender_name = sender_email if sender_email else house_name
        else:
            # Message d'un utilisateur
            display_sender_avatar = None
            if validate_avatar_file(sender_avatar_file):
                display_sender_avatar = f"/static/avatars/{sender_avatar_file}"
            elif sender_avatar_url:
                # Convertir v8 → v7 (fond transparent par défaut)
                if 'dicebear.com/8.x' in sender_avatar_url:
                    sender_avatar_url = sender_avatar_url.replace('dicebear.com/8.x', 'dicebear.com/7.x')
                display_sender_avatar = sender_avatar_url
            elif sender_avatar and len(str(sender_avatar)) <= 4:
                display_sender_avatar = sender_avatar
            elif sender_avatar:
                # C'est un seed DiceBear - construire l'URL
                sender_style = sender_avatar_style if sender_avatar_style else 'adventurer'
                display_sender_avatar = f"https://api.dicebear.com/7.x/{sender_style}/svg?seed={sender_avatar}&backgroundColor=transparent"
            else:
                display_sender_avatar = '👤'
            
            if not sender_name:
                sender_name = sender_email.split('@')[0] if sender_email else 'Inconnu'
        
        # Préparer l'avatar du destinataire
        display_recipient_avatar = None
        if validate_avatar_file(recipient_avatar_file):
            display_recipient_avatar = f"/static/avatars/{recipient_avatar_file}"
        elif recipient_avatar_url:
            # Convertir v8 → v7 (fond transparent par défaut)
            if 'dicebear.com/8.x' in recipient_avatar_url:
                recipient_avatar_url = recipient_avatar_url.replace('dicebear.com/8.x', 'dicebear.com/7.x')
            display_recipient_avatar = recipient_avatar_url
        elif recipient_avatar and len(str(recipient_avatar)) <= 4:
            display_recipient_avatar = recipient_avatar
        elif recipient_avatar:
            # C'est un seed DiceBear - construire l'URL
            recipient_style = recipient_avatar_style if recipient_avatar_style else 'adventurer'
            display_recipient_avatar = f"https://api.dicebear.com/7.x/{recipient_style}/svg?seed={recipient_avatar}&backgroundColor=transparent"
        else:
            display_recipient_avatar = '👤'
        
        if not recipient_name:
            recipient_name = recipient_email.split('@')[0] if recipient_email else 'Inconnu'
        
        messages_data.append({
            'id': msg_id,
            'sender_email': sender_email,
            'sender_name': sender_name,
            'sender_avatar': display_sender_avatar,
            'recipient_email': recipient_email,
            'recipient_name': recipient_name,
            'recipient_avatar': display_recipient_avatar,
            'content': content,
            'timestamp': timestamp,
            'sender_type': sender_type,
            'message_type': message_type,
            'is_me': sender_email == session['user'],
            'is_received_by_me': recipient_email == session['user'],
            'is_read_by_recipient': bool(is_read_by_recipient),
            'is_read_by_me': bool(is_read_by_me),
            'recipient_is_child': bool(recipient_is_child)
        })
    
    # ✅ Auto-marquer comme lu à l'ouverture (comportement WhatsApp : ouvrir = lire)
    for msg in messages_data:
        if msg['message_type'] == 'private':
            # Messages reçus directement par moi
            if msg['is_received_by_me'] and not msg['is_me'] and not msg['is_read_by_me']:
                mark_message_as_read(msg['id'], session['user'])
                msg['is_read_by_me'] = True
            # Messages pour un enfant : le parent lit au nom de l'enfant
            # (l'enfant n'a pas de téléphone, il consulte sur le téléphone du parent)
            if msg['recipient_is_child'] and not msg['is_read_by_recipient']:
                mark_message_as_read(msg['id'], msg['recipient_email'])
                msg['is_read_by_recipient'] = True

    # Récupérer tous les joueurs de la maison (sauf l'utilisateur actuel pour le sélecteur)
    _dbg(f"[DEBUG COMMENTS] house_id={house_id}, current_user={session['user']}")
    c.execute("""
        SELECT email, name, avatar, avatar_file, avatar_url, player_color
        FROM users 
        WHERE house_id = ? AND email != ?
    """, (house_id, session['user']))
    
    available_players = []
    players_result = c.fetchall()
    _dbg(f"[DEBUG COMMENTS] Nombre de joueurs trouvés (sans current_user): {len(players_result)}")
    
    for player_row in players_result:
        player_email, player_name, player_avatar, player_avatar_file, player_avatar_url, player_color = player_row
        _dbg(f"[DEBUG COMMENTS] Joueur: {player_name} ({player_email})")
        
        # Préparer l'avatar
        display_avatar = None
        if player_avatar_file:
            display_avatar = f"/static/avatars/{player_avatar_file}"
        elif player_avatar_url:
            # Convertir v8 → v7 (fond transparent par défaut)
            if 'dicebear.com/8.x' in player_avatar_url:
                player_avatar_url = player_avatar_url.replace('dicebear.com/8.x', 'dicebear.com/7.x')
            display_avatar = player_avatar_url
        elif player_avatar and len(str(player_avatar)) <= 4:
            display_avatar = player_avatar
        elif player_avatar:
            # C'est un seed DiceBear - construire l'URL
            # Récupérer le style de l'avatar
            try:
                c.execute("SELECT avatar_style FROM users WHERE email=?", (player_email,))
                style_row = c.fetchone()
                player_style = style_row[0] if style_row and style_row[0] else 'adventurer'
            except:
                player_style = 'adventurer'
            display_avatar = f"https://api.dicebear.com/7.x/{player_style}/svg?seed={player_avatar}&backgroundColor=transparent"
        else:
            # Aucun avatar - générer un DiceBear par défaut
            seed = player_email.split('@')[0] if player_email else 'default'
            display_avatar = f"https://api.dicebear.com/7.x/adventurer/svg?seed={seed}&backgroundColor=transparent"
        
        available_players.append({
            'email': player_email,
            'name': player_name if player_name else player_email.split('@')[0],
            'avatar': display_avatar,
            'color': player_color if player_color else '#4A90E2'
        })
    
    _dbg(f"[DEBUG COMMENTS] available_players count: {len(available_players)}")
    
    # Récupérer tous les joueurs pour l'affichage
    players = get_house_players_points(house_id)
    
    # Associer une couleur unique à chaque joueur (mêmes couleurs que task_page_enhanced)
    player_colors = [
        '#4A90E2',  # Bleu - Joueur 1
        '#9B59B6',  # Violet - Joueur 2
        '#27AE60',  # Vert - Joueur 3
        '#E67E22',  # Orange - Joueur 4
        '#E74C3C',  # Rouge - Joueur 5
        '#1ABC9C',  # Turquoise - Joueur 6
        '#F39C12',  # Jaune orange - Joueur 7
        '#3498DB',  # Bleu clair - Joueur 8
    ]
    
    # Créer un dictionnaire email -> couleur et email -> index
    color_map = {}
    color_index_map = {}
    for idx, player in enumerate(players):
        color_map[player['email']] = player_colors[idx % len(player_colors)]
        color_index_map[player['email']] = idx % len(player_colors)
    
    # Fonction helper pour convertir hex en rgba
    def hex_to_rgba(hex_color, alpha=0.25):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    
    # Ajouter la couleur à chaque available_player
    for player in available_players:
        player['color'] = color_map.get(player['email'], player_colors[0])
        player['color_rgba'] = hex_to_rgba(player['color'], 0.25)
    
    # Ajouter la couleur à chaque message
    for msg in messages_data:
        if msg['sender_type'] == 'house':
            # Messages de la maison - couleur selon le type
            if msg['message_type'] == 'baby_tracking':
                # Messages de suivi bébé - utiliser la couleur du joueur
                msg['color'] = color_map.get(msg['sender_email'], '#FFB6C1')  # Couleur du joueur ou rose par défaut
                msg['bg_color'] = hex_to_rgba(msg['color'], 0.15)  # Fond avec la couleur du joueur
            else:
                # Autres messages de la maison - couleur or/jaune
                msg['color'] = '#FDAE54'  # Or
                msg['bg_color'] = 'rgba(253, 174, 84, 0.15)'  # Fond or transparent
        elif msg['sender_type'] == 'system':
            # Couleurs différentes selon le type de message système
            if msg['message_type'] == 'task_completed':
                msg['color'] = '#27AE60'  # Vert pour validation de tâche
                msg['bg_color'] = 'rgba(39, 174, 96, 0.15)'  # Fond vert transparent
            elif msg['message_type'] == 'task_added':
                msg['color'] = '#F39C12'  # Orange pour ajout de tâche
                msg['bg_color'] = 'rgba(243, 156, 18, 0.15)'  # Fond orange transparent
            else:
                msg['color'] = '#A6D3DC'  # Couleur teal pour messages de la maison
                msg['bg_color'] = 'rgba(166, 211, 220, 0.15)'  # Fond teal transparent
        else:
            # Messages de chat des joueurs
            msg['color'] = color_map.get(msg['sender_email'], '#4A90E2')
            msg['bg_color'] = 'rgba(255, 255, 255, 0.15)'  # Fond blanc transparent
    
    # Compter les messages non lus
    unread_count = get_unread_message_count(session['user'], house_id)

    conn.close()

    return render_template('comments.html', 
                         messages=messages_data,
                         email=session['user'], 
                         players=players,
                         available_players=available_players,
                         house_code=house_code,
                         house_name=house_name,
                         current_user_name=current_user_name,
                         unread_count=unread_count,
                         menu_page=True)

@app.route('/baby_messages')
def baby_messages():
    """
    Page dédiée aux messages de tracking bébé uniquement.
    Accessible via le bouton rose sous le menu burger.
    
    COMPORTEMENT :
    - Messages consultables uniquement (pas de notif, pas de marquage lu/non-lu)
    - Suppression automatique après 1 mois
    - Historique visible par tous les membres de la maison
    """
    if 'user' not in session:
        flash("Connecte-toi pour accéder aux messages bébé", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        flash("Tu dois rejoindre une maison pour accéder aux messages", "warning")
        return redirect(url_for('menu'))
    
    house_id = user_row[0]
    current_user_name = user_row[1] if user_row[1] else session['user'].split('@')[0]

    # 🗑️ NETTOYAGE AUTOMATIQUE : Supprimer les messages de plus d'un mois
    from datetime import datetime, timedelta
    one_month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    
    c.execute("""
        DELETE FROM messages 
        WHERE house_id = ? 
        AND message_type = 'baby_tracking' 
        AND timestamp < ?
    """, (house_id, one_month_ago))
    deleted_count = c.rowcount
    if deleted_count > 0:
        _dbg(f"🗑️ Supprimé {deleted_count} messages baby_tracking de plus d'un mois pour house_id={house_id}")
    conn.commit()

    # Récupérer le code et le nom de la maison
    c.execute("SELECT code, name FROM houses WHERE id=?", (house_id,))
    house_row = c.fetchone()
    house_code = house_row[0] if house_row else None
    house_name = house_row[1] if house_row and house_row[1] else 'Ma Maison'

    # Récupérer UNIQUEMENT les messages de type baby_tracking (moins d'un mois)
    _dbg(f"🔍 /baby_messages - Récupération messages bébé pour house_id={house_id}")
    c.execute("""
        SELECT m.id, m.sender_email, m.recipient_email, m.content, m.timestamp, m.sender_type, m.message_type,
               sender.name, sender.avatar, sender.avatar_file, sender.avatar_url, sender.avatar_style,
               CASE WHEN EXISTS (
                   SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?
               ) THEN 1 ELSE 0 END as is_read_by_me
        FROM messages m
        LEFT JOIN users sender ON m.sender_email = sender.email
        WHERE m.house_id = ?
        AND m.message_type = 'baby_tracking'
        ORDER BY m.id DESC
        LIMIT 100
    """, (session['user'], house_id))
    
    all_rows = c.fetchall()
    _dbg(f"🔍 /baby_messages - Nombre de messages bébé récupérés: {len(all_rows)}")
    
    messages_data = []
    for row in all_rows:
        msg_id, sender_email, recipient_email, content, timestamp, sender_type, message_type, sender_name, sender_avatar, sender_avatar_file, sender_avatar_url, sender_avatar_style, is_read_by_me = row
        
        # Préparer l'avatar de l'expéditeur
        display_sender_avatar = None
        if validate_avatar_file(sender_avatar_file):
            display_sender_avatar = f"/static/avatars/{sender_avatar_file}"
        elif sender_avatar_url:
            if 'dicebear.com/8.x' in sender_avatar_url:
                sender_avatar_url = sender_avatar_url.replace('dicebear.com/8.x', 'dicebear.com/7.x')
            display_sender_avatar = sender_avatar_url
        elif sender_avatar and len(str(sender_avatar)) <= 4:
            display_sender_avatar = sender_avatar
        elif sender_avatar:
            sender_style = sender_avatar_style if sender_avatar_style else 'adventurer'
            display_sender_avatar = f"https://api.dicebear.com/7.x/{sender_style}/svg?seed={sender_avatar}&backgroundColor=transparent"
        else:
            display_sender_avatar = '👤'
        
        if not sender_name or sender_name.strip() == '':
            sender_name = sender_email.split('@')[0] if sender_email else 'Inconnu'
        
        messages_data.append({
            'id': msg_id,
            'sender_email': sender_email,
            'sender_name': sender_name,
            'sender_avatar': display_sender_avatar,
            'content': content,
            'timestamp': timestamp,
            'sender_type': sender_type,
            'message_type': message_type,
            'is_me': sender_email == session['user'],
            'is_read_by_me': bool(is_read_by_me),
            'color': '#F472B6',  # Rose pour les messages bébé
            'bg_color': 'rgba(244, 114, 182, 0.15)'
        })

    # ✅ Auto-marquer comme lu tous les messages des autres joueurs (ouvrir = lire)
    for msg in messages_data:
        if not msg['is_me'] and not msg['is_read_by_me']:
            mark_message_as_read(msg['id'], session['user'])
            msg['is_read_by_me'] = True

    # Récupérer tous les joueurs pour l'affichage
    players = get_house_players_points(house_id)
    
    conn.close()

    return render_template('baby_messages.html', 
                         messages=messages_data,
                         email=session['user'], 
                         players=players,
                         house_code=house_code,
                         house_name=house_name,
                         current_user_name=current_user_name,
                         menu_page=True)

@app.route('/mark_all_messages_read', methods=['POST'])
def mark_all_messages_read():
    """
    Marque tous les messages reçus par l'utilisateur comme lus.
    Retourne le nouveau compteur de messages non lus.
    """
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'error': 'Pas de maison'}), 400
    
    house_id = user_row[0]
    
    # Récupérer tous les messages non lus reçus par l'utilisateur
    # ⚠️ Utiliser la MÊME logique que get_unread_message_count pour éviter les décalages
    c.execute("""
        SELECT m.id, m.sender_email
        FROM messages m
        WHERE m.house_id = ?
        AND (m.sender_email IS NULL OR m.sender_email != ?)
        AND m.message_type NOT IN ('task_completed', 'baby_tracking', 'task_added')
        AND (
            (m.message_type = 'private' AND (m.sender_email = ? OR m.recipient_email = ?))
            OR (m.sender_type = 'house')
        )
        AND m.id NOT IN (
            SELECT message_id FROM message_reads WHERE user_email = ?
        )
    """, (house_id, session['user'], session['user'], session['user'], session['user']))
    
    unread_rows = c.fetchall()
    unread_message_ids = [row[0] for row in unread_rows]
    impacted_senders = set()
    for _, sender_email in unread_rows:
        if sender_email and sender_email != session['user']:
            impacted_senders.add(sender_email)
    
    # Marquer tous ces messages comme lus
    for msg_id in unread_message_ids:
        mark_message_as_read(msg_id, session['user'])
    
    # Récupérer le nouveau compteur
    unread_count = get_unread_message_count(session['user'], house_id)
    unread_by_sender = get_unread_messages_by_sender(session['user'], house_id)
    
    # ✅ MESSAGERIE TYPE IPHONE : Pas de statut "lu" pour les messages envoyés
    # On ne notifie que les messages REÇUS
    
    # Notifier via WebSocket avec protection contre sessions invalides
    safe_socketio_emit('unread_count_update', {
        'count': unread_count,
        'user_email': session['user'],
        'unread_by_sender': unread_by_sender
    }, room=f'house_{house_id}', namespace='/', broadcast=True)
    
    # Notifier que cet utilisateur a tout lu (pour mettre à jour l'UI des autres)
    safe_socketio_emit('all_messages_read', {
        'reader_email': session['user'],
        'message_ids': unread_message_ids
    }, room=f'house_{house_id}', namespace='/', broadcast=True)

    # Forcer un refresh des compteurs côté menu/comments sur tous les appareils.
    safe_socketio_emit('messages_list_update', {
        'house_id': house_id,
        'action': 'all_read',
        'reader_email': session['user']
    }, room=f'house_{house_id}', namespace='/', broadcast=True)
    
    conn.close()
    
    return jsonify({
        'success': True,
        'unread_count': unread_count,
        'marked_count': len(unread_message_ids)
    })


@app.route('/mark_single_message_read_for_child', methods=['POST'])
def mark_single_message_read_for_child():
    """
    Permet à un parent de marquer UN seul message comme lu au nom d'un enfant.
    Utilisé quand le parent lit un message spécifique à l'enfant.
    """
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    data = request.get_json() or request.form
    message_id = data.get('message_id')
    child_email = data.get('child_email')
    
    if not message_id or not child_email:
        return jsonify({'success': False, 'error': 'Paramètres manquants'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Vérifier que l'utilisateur et l'enfant sont dans la même maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'error': 'Pas de maison'}), 400
    
    house_id = user_row[0]
    
    # Vérifier que le message existe et que le destinataire est l'enfant
    c.execute("""
        SELECT id, recipient_email, message_type 
        FROM messages 
        WHERE id = ? AND house_id = ? AND recipient_email = ?
    """, (message_id, house_id, child_email))
    
    msg_row = c.fetchone()
    if not msg_row:
        conn.close()
        return jsonify({'success': False, 'error': 'Message non trouvé'}), 404
    
    message_type = msg_row[2]
    
    # Marquer le message comme lu au nom de l'enfant
    if not mark_message_as_read(message_id, child_email):
        conn.close()
        return jsonify({'success': False, 'error': 'Impossible de marquer ce message comme lu'}), 500
    
    # Calculer le nouveau nombre de messages non lus pour cet enfant (envoyés par l'utilisateur courant)
    c.execute("""
        SELECT COUNT(*) FROM messages m
        WHERE m.house_id = ?
        AND m.sender_email = ?
        AND m.recipient_email = ?
        AND m.message_type = 'private'
        AND m.id NOT IN (SELECT message_id FROM message_reads WHERE user_email = ?)
    """, (house_id, session['user'], child_email, child_email))
    new_unread_count = c.fetchone()[0]
    
    conn.close()
    
    # Émettre un événement WebSocket pour mettre à jour les pastilles en temps réel
    safe_socketio_emit('badge_update', {
        'child_email': child_email,
        'new_count': new_unread_count,
        'updated_by': session['user']
    }, room=f'house_{house_id}', namespace='/', broadcast=True)
    
    # Notifier que le message a été marqué comme lu (pour synchroniser l'UI en temps réel)
    safe_socketio_emit('message_read_update', {
        'message_id': int(message_id),
        'reader_email': child_email,
        'read_by': session['user']
    }, room=f'house_{house_id}', namespace='/', broadcast=True)
    
    return jsonify({
        'success': True,
        'message_id': message_id,
        'child_email': child_email,
        'new_unread_count': new_unread_count
    })

@app.route('/mark_single_message_read', methods=['POST'])
def mark_single_message_read():
    """
    Permet à l'utilisateur de marquer UN seul message reçu comme lu.
    Utilisé pour marquer individuellement les messages reçus.
    """
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    data = request.get_json() or request.form
    message_id = data.get('message_id')
    
    if not message_id:
        return jsonify({'success': False, 'error': 'ID de message manquant'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Vérifier que l'utilisateur a une maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'error': 'Pas de maison'}), 400
    
    house_id = user_row[0]
    
    # Vérifier que le message existe et que :
    # - soit l'utilisateur est le destinataire (recipient_email = user)
    # - soit c'est un message "house" (sender_type = 'house', recipient_email vide/null)
    c.execute("""
        SELECT id, recipient_email, sender_email, sender_type, message_type 
        FROM messages 
        WHERE id = ? AND house_id = ? 
        AND (recipient_email = ? OR (sender_type = 'house' AND (recipient_email IS NULL OR recipient_email = '')))
    """, (message_id, house_id, session['user']))
    
    msg_row = c.fetchone()
    if not msg_row:
        conn.close()
        return jsonify({'success': False, 'error': 'Message non trouvé'}), 404
    
    sender_email = msg_row[2]
    message_type = msg_row[4]
    
    # Marquer le message comme lu
    if not mark_message_as_read(message_id, session['user']):
        conn.close()
        return jsonify({'success': False, 'error': 'Impossible de marquer ce message comme lu'}), 500
    
    # Calculer le nouveau nombre total de messages non lus
    unread_count = get_unread_message_count(session['user'], house_id)
    unread_by_sender = get_unread_messages_by_sender(session['user'], house_id)
    unread_sent_to = get_unread_messages_sent_to(session['user'], house_id)

    sender_unread_sent_to = {}
    if sender_email and sender_email != session['user']:
        sender_unread_sent_to = get_unread_messages_sent_to(sender_email, house_id)
    
    conn.close()
    
    # Émettre un événement WebSocket pour mettre à jour les badges en temps réel
    safe_socketio_emit('unread_count_update', {
        'count': unread_count,
        'user_email': session['user'],
        'unread_by_sender': unread_by_sender,
        'unread_sent_to': unread_sent_to
    }, room=f'house_{house_id}', namespace='/', broadcast=True)

    if sender_email and sender_email != session['user']:
        safe_socketio_emit('unread_sent_to_update', {
            'user_email': sender_email,
            'unread_sent_to': sender_unread_sent_to
        }, room=f'house_{house_id}', namespace='/', broadcast=True)
    
    # Notifier que le message a été marqué comme lu (pour synchroniser l'UI en temps réel)
    safe_socketio_emit('message_read_update', {
        'message_id': int(message_id),
        'reader_email': session['user'],
        'read_by': session['user']
    }, room=f'house_{house_id}', namespace='/', broadcast=True)

    safe_socketio_emit('messages_list_update', {
        'house_id': house_id,
        'action': 'message_read',
        'reader_email': session['user'],
        'message_id': int(message_id)
    }, room=f'house_{house_id}')
    
    return jsonify({
        'success': True,
        'message_id': message_id,
        'sender_email': sender_email,
        'new_unread_count': unread_count,
        'unread_by_sender': unread_by_sender,
        'unread_sent_to': unread_sent_to
    })


@app.route('/api/unread_messages_count', methods=['GET'])
def api_unread_messages_count():
    """
    API pour récupérer le nombre de messages non lus de l'utilisateur actuel.
    Utilisé pour rafraîchir les badges après réception d'un message pour enfant.
    """
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer la maison de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_row = c.fetchone()
        if not user_row or not user_row[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Pas de maison'}), 400
        
        house_id = user_row[0]
        
        # Compter les messages non lus
        unread_count = get_unread_message_count(session['user'], house_id, existing_conn=conn)
        unread_by_sender = get_unread_messages_by_sender(session['user'], house_id, existing_conn=conn)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'unread_count': unread_count,
            'unread_by_sender': unread_by_sender
        })
    except Exception as e:
        _dbg(f"❌ Erreur API unread_messages_count: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500


@app.route('/mark_messages_read_for_child', methods=['POST'])
def mark_messages_read_for_child():
    """
    Permet à un parent de marquer les messages comme lus au nom d'un enfant.
    Utilisé quand le parent lit les messages à l'enfant en personne.
    """
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    data = request.get_json() or request.form
    child_email = data.get('child_email')
    
    if not child_email:
        return jsonify({'success': False, 'error': 'Email enfant manquant'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Vérifier que l'utilisateur et l'enfant sont dans la même maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'error': 'Pas de maison'}), 400
    
    house_id = user_row[0]
    
    c.execute("SELECT house_id, email FROM users WHERE email=? AND house_id=?", (child_email, house_id))
    child_row = c.fetchone()
    if not child_row:
        conn.close()
        return jsonify({'success': False, 'error': 'Enfant non trouvé dans cette maison'}), 400
    
    # Récupérer tous les messages privés envoyés À cet enfant et non encore lus par lui
    c.execute("""
        SELECT m.id
        FROM messages m
        WHERE m.house_id = ?
        AND m.recipient_email = ?
        AND m.message_type = 'private'
        AND m.id NOT IN (
            SELECT message_id FROM message_reads WHERE user_email = ?
        )
    """, (house_id, child_email, child_email))
    
    unread_message_ids = [row[0] for row in c.fetchall()]
    
    # Marquer tous ces messages comme lus au nom de l'enfant
    for msg_id in unread_message_ids:
        mark_message_as_read(msg_id, child_email)
    
    conn.close()
    
    return jsonify({
        'success': True,
        'marked_count': len(unread_message_ids),
        'child_email': child_email
    })


# ══════════════════════════════════════════════════════════════════════════
# 🧪 FEEDBACK TESTEURS BÊTA
# ══════════════════════════════════════════════════════════════════════════

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """Formulaire de feedback pour les testeurs bêta"""
    if 'user' not in session:
        return redirect(url_for('welcome'))

    user_email = session.get('user')
    user_name = session.get('player_name', '')

    if request.method == 'POST':
        try:
            note_globale = request.form.get('note_globale') or None
            note_facilite = request.form.get('note_facilite') or None
            note_design = request.form.get('note_design') or None
            ce_qui_plait = request.form.get('ce_qui_plait', '').strip() or None
            ce_qui_deplait = request.form.get('ce_qui_deplait', '').strip() or None
            ameliorations = request.form.get('ameliorations', '').strip() or None
            pret_a_payer = int(request.form.get('pret_a_payer', 0))
            prix_acceptable = request.form.get('prix_acceptable', '').strip() or None
            recommande_raw = request.form.get('recommande', '')
            recommande = int(recommande_raw) if recommande_raw.strip() in ('0', '1') else None
            autres_commentaires = request.form.get('autres_commentaires', '').strip() or None

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO beta_feedback
                    (user_email, user_name, note_globale, note_facilite, note_design,
                     ce_qui_plait, ce_qui_deplait, ameliorations,
                     pret_a_payer, prix_acceptable, recommande, autres_commentaires)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_email, user_name,
                int(note_globale) if note_globale else None,
                int(note_facilite) if note_facilite else None,
                int(note_design) if note_design else None,
                ce_qui_plait, ce_qui_deplait, ameliorations,
                pret_a_payer, prix_acceptable, recommande, autres_commentaires
            ))
            conn.commit()
            conn.close()
            return render_template('feedback.html', submitted=True)
        except Exception as e:
            _dbg(f"❌ Erreur feedback: {e}")
            flash("Une erreur s'est produite. Réessaie.", "error")
            return render_template('feedback.html', submitted=False)

    return render_template('feedback.html', submitted=False)


# Clé secrète admin (à changer !) — accessible via /admin_feedback?key=CETTE_CLE
ADMIN_FEEDBACK_KEY = os.environ.get("ADMIN_FEEDBACK_KEY", "cleanbeat_admin_2026")


@app.route('/admin_feedback')
def admin_feedback():
    """Page admin pour lire les feedbacks (protégée par clé URL)"""
    key = request.args.get('key', '')
    if key != ADMIN_FEEDBACK_KEY:
        return "Accès refusé. Ajoute ?key=VOTRE_CLE à l'URL.", 403

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, submitted_at, user_email, user_name,
               note_globale, note_facilite, note_design,
               ce_qui_plait, ce_qui_deplait, ameliorations,
               pret_a_payer, prix_acceptable, recommande, autres_commentaires
        FROM beta_feedback
        ORDER BY submitted_at DESC
    """)
    rows = c.fetchall()
    conn.close()

    # Convertir en liste de dicts
    keys = ['id', 'submitted_at', 'user_email', 'user_name',
            'note_globale', 'note_facilite', 'note_design',
            'ce_qui_plait', 'ce_qui_deplait', 'ameliorations',
            'pret_a_payer', 'prix_acceptable', 'recommande', 'autres_commentaires']
    feedbacks = [dict(zip(keys, row)) for row in rows]
    return render_template('admin_feedback.html', feedbacks=feedbacks)


@app.route('/admin_feedback_csv')
def admin_feedback_csv():
    """Export CSV des feedbacks"""
    key = request.args.get('key', '')
    if key != ADMIN_FEEDBACK_KEY:
        return "Accès refusé.", 403

    import csv
    import io
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM beta_feedback ORDER BY submitted_at DESC")
    rows = c.fetchall()
    col_names = [description[0] for description in c.description]
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(col_names)
    writer.writerows(rows)
    csv_content = output.getvalue()
    output.close()

    from flask import Response
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=feedbacks_cleanbeat.csv'}
    )


@app.route('/rewards')
def rewards():
    import json
    if 'user' not in session:
        flash("Connecte-toi pour accéder aux récompenses", "warning")
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer la maison de l'utilisateur
        c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
        user_row = c.fetchone()
        if not user_row or not user_row[0]:
            conn.close()
            flash("Tu dois rejoindre une maison pour accéder aux récompenses", "warning")
            return redirect(url_for('menu'))
    except Exception as e:
        print(f"❌ Erreur rewards: {e}", flush=True)
        return redirect(url_for('menu'))
    
    house_id = user_row[0]
    user_name = user_row[1]
    
    # ⚡ Vérifier et effectuer la réinitialisation hebdomadaire des statistiques si nécessaire
    check_weekly_reset(house_id, conn)
    
    # Récupérer le code de la maison
    c.execute("SELECT code FROM houses WHERE id=?", (house_id,))
    house_code = c.fetchone()[0]
    
    # Vérifier si c'est dimanche après 6h du matin
    # TEMPORAIREMENT DÉSACTIVÉ POUR TEST - remettre les lignes suivantes pour la prod
    from datetime import datetime, timedelta
    now = datetime.now()
    # is_sunday = now.weekday() == 6  # 6 = dimanche
    # is_after_6am = now.hour >= 6
    # can_open = is_sunday and is_after_6am
    can_open = True  # TEMP: Toujours accessible pour les tests
    
    # Déterminer le gagnant de la semaine (celui avec le plus de points cette semaine)
    today = datetime.now()
    start_of_week = (today - timedelta(days=today.weekday())).date().isoformat()
    
    c.execute("""
        SELECT u.email, u.name, COALESCE(SUM(ct.points), 0) as weekly_points
        FROM users u
        LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
            AND DATE(ct.completed_at) >= ?
        WHERE u.house_id = ?
        GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style
        ORDER BY weekly_points DESC
        LIMIT 1
    """, (start_of_week, house_id))
    
    winner_row = c.fetchone()
    is_winner = False
    winner_name = ""
    
    if winner_row:
        winner_email = winner_row[0]
        winner_name = winner_row[1]
        is_winner = (winner_email == session['user'])
    
    # Créer la table si elle n'existe pas avec colonne pour la semaine
    c.execute("""
        CREATE TABLE IF NOT EXISTS reward_boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_id INTEGER NOT NULL,
            box_number INTEGER NOT NULL,
            reward_text TEXT NOT NULL,
            opened_by TEXT NOT NULL,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            week_start DATE NOT NULL,
            FOREIGN KEY (house_id) REFERENCES houses(id),
            FOREIGN KEY (opened_by) REFERENCES users(email)
        )
    """)
    
    # Ajouter les colonnes manquantes si elles n'existent pas
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN week_start DATE")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN box_number INTEGER")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN reward_text TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN opened_by TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass
    
    # Vérifier si l'utilisateur a déjà ouvert une case cette semaine
    c.execute("""
        SELECT box_number, reward_text FROM reward_boxes 
        WHERE house_id=? AND opened_by=? AND week_start=?
    """, (house_id, session['user'], start_of_week))
    user_opened_this_week = c.fetchone()
    already_opened_this_week = user_opened_this_week is not None
    last_reward = user_opened_this_week[1] if user_opened_this_week else ""
    
    # Récupérer toutes les cases ouvertes pour cette maison (historique)
    # TEMPORAIREMENT DÉSACTIVÉ POUR TEST - on renvoie une liste vide
    # c.execute("SELECT box_number FROM reward_boxes WHERE house_id=?", (house_id,))
    # opened_boxes = [row[0] for row in c.fetchall()]
    opened_boxes = []  # Mode test - toutes les cases apparaissent comme non ouvertes
    
    # Récupérer le type de foyer (avec gestion d'erreur si la colonne n'existe pas)
    try:
        c.execute("SELECT house_type FROM houses WHERE id=?", (house_id,))
        house_type_row = c.fetchone()
        house_type = house_type_row[0] if house_type_row and house_type_row[0] else 'family'
    except Exception as e:
        _dbg(f"⚠️ Erreur récupération house_type: {e}")
        house_type = 'family'  # Valeur par défaut
    
    # Créer la table des récompenses personnalisées si elle n'existe pas
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_id INTEGER NOT NULL,
            house_type TEXT NOT NULL,
            rewards_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (house_id) REFERENCES houses(id),
            UNIQUE(house_id, house_type)
        )
    """)
    
    # Ajouter les colonnes manquantes si elles n'existent pas
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN house_type TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN rewards_json TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass
    
    # Charger les récompenses personnalisées ou utiliser les valeurs par défaut
    c.execute("SELECT rewards_json FROM custom_rewards WHERE house_id=? AND house_type=?", (house_id, 'family'))
    family_custom = c.fetchone()
    
    c.execute("SELECT rewards_json FROM custom_rewards WHERE house_id=? AND house_type=?", (house_id, 'couple'))
    couple_custom = c.fetchone()
    
    c.execute("SELECT rewards_json FROM custom_rewards WHERE house_id=? AND house_type=?", (house_id, 'coloc'))
    coloc_custom = c.fetchone()
    
    conn.close()
    
    # MODE TEST: Forcer l'accès à la grille pour gérer les cadeaux
    already_opened_this_week = False  # Désactivé pour les tests
    
    # Préparer les trois grilles pour affichage - Récompenses par défaut
    default_rewards_family = [
        "Choisir le menu du dîner", "Veiller plus tard le soir", "Inviter un copain à dormir",
        "Choisir le film familial", "Avoir le droit de sauter le bain", "Manger son dessert préféré",
        "Choisir l'activité du week-end", "Recevoir un petit jouet/livre surprise", "Avoir du temps d'écran bonus",
        "Dormir dans le lit des parents", "Une sortie spéciale parent-enfant au choix",
        "Jouer à son jeu préféré avec papa/maman", "Lire une histoire de plus au coucher",
        "Faire une activité créative avec les parents", "Aller au parc/aire de jeux",
        "Choisir la musique en voiture", "Faire des crêpes/gaufres ensemble",
        "Session câlins et chatouilles", "Pique-niquer dans le salon",
        "Construire une cabane ensemble", "Passer son tour pour ranger sa chambre",
        "Choisir ses vêtements (même bizarres)", "Manger avec les doigts",
        "Ne pas finir ses légumes", "Avoir le droit de faire du bruit",
        "Porter son pyjama toute la journée", "Manger le petit-déjeuner au lit",
        "Sauter la routine des devoirs", "Avoir un goûter spécial",
        "Choisir son petit-déjeuner", "Recevoir une médaille/diplôme fait maison",
        "Être le 'chef de famille' pour la journée", "Organiser une chasse au trésor par les parents",
        "Faire une soirée pyjama dans le salon", "Avoir un jour 'oui' (parents disent oui à tout le raisonnable)",
        "Recevoir des autocollants collector", "Préparer un gâteau avec maman/papa",
        "Aller chercher une surprise au magasin", "Avoir une journée 'bon élève' sans corvées",
        "Organiser une mini-fête à la maison"
    ]
    
    default_rewards_couple = [
        "Massage complet", "Petit-déjeuner au lit préparé par l'autre", "Soirée spa maison",
        "Bain aux chandelles préparé", "Être dispensé de cuisine", "Dîner aux chandelles maison",
        "Soirée cinéma avec snacks préférés", "Grasse matinée sans réveil",
        "Avoir la salle de bain en premier", "Choisir la température de la chambre",
        "Date night planifiée et payée par l'autre", "Week-end sans parler de tâches domestiques",
        "Soirée jeux à deux", "Promenade main dans la main", "Danser ensemble dans le salon",
        "Session photo couple rigolote", "Écrire une lettre d'amour",
        "Regarder le lever/coucher de soleil ensemble", "Pique-niquer à deux",
        "Soirée karaoké privée", "Choisir tous les films/séries",
        "Contrôle total de la télécommande", "Avoir le côté du lit préféré",
        "Ne pas faire la vaisselle", "Être servi son café/thé au réveil",
        "Choisir la musique de la maison", "Avoir la couette entière",
        "Dormir sans être réveillé", "Choisir les sorties",
        "Avoir le dernier mot sur la déco", "Strip poker version corvées",
        "Massage sensuel aux huiles", "Soirée costumée à deux",
        "Jeu de vérité ou action", "Chasse au trésor coquine dans la maison",
        "Soirée dégustation (vin, fromage, chocolat)", "Cours de danse improvisé",
        "Karaoké love songs", "Session photos boudoir amateur",
        "Nuit d'hôtel ou escapade surprise"
    ]
    
    default_rewards_coloc = [
        "Passer son tour de ménage", "Choisir la température de l'appart",
        "Avoir la salle de bain en premier", "Utiliser la machine à laver en priorité",
        "Avoir le meilleur spot de parking/rangement vélo", "Choisir l'organisation du frigo",
        "Ne pas sortir les poubelles", "Être dispensé de vaisselle",
        "Avoir la télécommande TV", "Choisir le parfum des produits ménagers",
        "Les autres préparent ton plat préféré", "Avoir le droit de finir les restes premium",
        "Se faire livrer un resto aux frais des autres", "Avoir l'étagère du frigo la plus accessible",
        "Choisir les courses", "Recevoir un dessert surprise", "Ne pas cuisiner",
        "Avoir le droit aux meilleurs snacks", "Organiser un apéro payé par les colocs",
        "Choisir le resto pour la prochaine sortie groupe", "Monopoliser le salon pour une soirée",
        "Mettre sa musique à fond", "Organiser une soirée avec ses amis",
        "Avoir la paix absolue", "Choisir la déco des espaces communs",
        "Utiliser l'espace commun pour son hobby", "Avoir le meilleur siège du salon",
        "Faire du bruit sans plainte possible", "Occuper la cuisine pour un projet culinaire",
        "Réorganiser un espace commun à son goût", "Obliger les colocs à faire une soirée jeux",
        "Organiser une soirée thématique", "Choisir le film de la soirée coloc",
        "Imposer une journée pyjama collectif", "Recevoir un trophée/médaille ridicule",
        "Avoir un titre honorifique affiché ('Maître du balai')",
        "Les colocs doivent porter un accessoire ridicule", "Organiser un concours débile",
        "Créer une règle absurde", "Avoir un 'joker silence' (faire taire les colocs quand on veut)"
    ]
    
    # Utiliser les récompenses personnalisées si elles existent, sinon les valeurs par défaut
    try:
        rewards_family_list = json.loads(family_custom[0]) if family_custom else default_rewards_family
    except Exception as e:
        _dbg(f"⚠️ Erreur parsing JSON family rewards: {e}")
        rewards_family_list = default_rewards_family
    
    try:
        rewards_couple_list = json.loads(couple_custom[0]) if couple_custom else default_rewards_couple
    except Exception as e:
        _dbg(f"⚠️ Erreur parsing JSON couple rewards: {e}")
        rewards_couple_list = default_rewards_couple
    
    try:
        rewards_coloc_list = json.loads(coloc_custom[0]) if coloc_custom else default_rewards_coloc
    except Exception as e:
        _dbg(f"⚠️ Erreur parsing JSON coloc rewards: {e}")
        rewards_coloc_list = default_rewards_coloc

    try:
        response = make_response(render_template('rewards.html', 
                             house_code=house_code, 
                             is_winner=is_winner,
                             winner_name=winner_name,
                             user_name=user_name,
                             opened_boxes=opened_boxes,
                             can_open=can_open,
                             already_opened_this_week=already_opened_this_week,
                             last_reward=last_reward,
                             email=session['user'],
                             rewards_family=rewards_family_list,
                             rewards_couple=rewards_couple_list,
                             rewards_coloc=rewards_coloc_list,
                             house_type=house_type))
        
        # Empêcher la mise en cache
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    except Exception as e:
        _dbg(f"❌ Erreur dans /rewards: {e}")
        import traceback
        traceback.print_exc()
        flash("Une erreur s'est produite lors du chargement de la grille", "danger")
        return redirect(url_for('menu'))


@app.route('/update_rewards', methods=['POST'])
def update_rewards():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'}), 401
    
    data = request.get_json()
    house_type = data.get('house_type')
    rewards = data.get('rewards')
    
    if not house_type or not rewards:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400
    
    if not isinstance(rewards, list) or len(rewards) != 40:
        return jsonify({'success': False, 'message': 'Il faut exactement 40 récompenses'}), 400
    
    # Valider que toutes les récompenses sont des chaînes non vides
    for reward in rewards:
        if not isinstance(reward, str) or not reward.strip():
            return jsonify({'success': False, 'message': 'Toutes les récompenses doivent être remplies'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'message': 'Pas de maison'}), 400
    
    house_id = user_row[0]
    
    # Sauvegarder les récompenses personnalisées
    rewards_json = json.dumps(rewards, ensure_ascii=False)
    
    try:
        c.execute("""
            INSERT INTO custom_rewards (house_id, house_type, rewards_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(house_id, house_type) 
            DO UPDATE SET rewards_json=?, updated_at=CURRENT_TIMESTAMP
        """, (house_id, house_type, rewards_json, rewards_json))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Récompenses sauvegardées'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500




@app.route('/open_reward_box', methods=['POST'])
def open_reward_box():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'}), 401
    
    box_number = request.json.get('box_number')
    
    if not box_number or not isinstance(box_number, int) or box_number < 1 or box_number > 40:
        return jsonify({'success': False, 'message': 'Numéro de case invalide'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'message': 'Pas de maison'}), 400
    
    house_id = user_row[0]
    
    # Vérifier si c'est dimanche après 6h du matin
    # TEMPORAIREMENT DÉSACTIVÉ POUR TEST
    from datetime import datetime, timedelta
    now = datetime.now()
    # is_sunday = now.weekday() == 6
    # is_after_6am = now.hour >= 6
    # if not (is_sunday and is_after_6am):
    #     conn.close()
    #     return jsonify({'success': False, 'message': 'La grille cadeau mystère est disponible uniquement le dimanche à partir de 6h !'}), 403
    
    # TEMP: Pas de vérification pour les tests
    
    # Calculer le début de la semaine
    today = datetime.now()
    start_of_week = (today - timedelta(days=today.weekday())).date().isoformat()
    
    # Vérifier que l'utilisateur est le gagnant de la semaine
    c.execute("""
        SELECT u.email, COALESCE(SUM(ct.points), 0) as weekly_points
        FROM users u
        LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
            AND DATE(ct.completed_at) >= ?
        WHERE u.house_id = ?
        GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style
        ORDER BY weekly_points DESC
        LIMIT 1
    """, (start_of_week, house_id))
    
    winner_row = c.fetchone()
    # TEMPORAIREMENT DÉSACTIVÉ POUR TEST - vérification du gagnant
    # if not winner_row or winner_row[0] != session['user']:
    #     conn.close()
    #     return jsonify({'success': False, 'message': 'Seul le gagnant de la semaine peut ouvrir une case'}), 403
    
    # TEMPORAIREMENT DÉSACTIVÉ POUR TEST - vérification déjà ouvert cette semaine
    # c.execute("SELECT box_number FROM reward_boxes WHERE house_id=? AND opened_by=? AND week_start=?", 
    #           (house_id, session['user'], start_of_week))
    # if c.fetchone():
    #     conn.close()
    #     return jsonify({'success': False, 'message': 'Tu as déjà ouvert ton cadeau mystère cette semaine !'}), 400
    
    # === GRILLES DE RÉCOMPENSES PAR TYPE DE FOYER ===
    
    # Récupérer le type de foyer de la maison pour choisir la bonne grille
    c.execute("SELECT house_type FROM houses WHERE id=?", (house_id,))
    house_type_row = c.fetchone()
    house_type = house_type_row[0] if house_type_row and house_type_row[0] else 'family'
    
    _dbg(f"[DEBUG open_reward_box] house_id={house_id}, house_type={house_type}, box_number={box_number}")
    
    # Créer la table custom_rewards si elle n'existe pas
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_id INTEGER NOT NULL,
            house_type TEXT NOT NULL,
            rewards_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (house_id) REFERENCES houses(id),
            UNIQUE(house_id, house_type)
        )
    """)
    
    # Ajouter les colonnes manquantes si elles n'existent pas
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN house_type TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN rewards_json TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass
    
    # Créer la table reward_boxes si elle n'existe pas
    c.execute("""
        CREATE TABLE IF NOT EXISTS reward_boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_id INTEGER NOT NULL,
            box_number INTEGER NOT NULL,
            reward_text TEXT NOT NULL,
            opened_by TEXT NOT NULL,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            week_start DATE NOT NULL,
            FOREIGN KEY (house_id) REFERENCES houses(id),
            FOREIGN KEY (opened_by) REFERENCES users(email)
        )
    """)
    
    # Ajouter les colonnes manquantes pour reward_boxes si elles n'existent pas
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN week_start DATE")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN box_number INTEGER")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN reward_text TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN opened_by TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass
    
    # Charger les récompenses personnalisées ou les récompenses par défaut
    # Grille Parents/Enfants (40 récompenses par défaut)
    default_rewards_family = [
        # Privilèges quotidiens (1-10)
        {"text": "Choisir le menu du dîner", "image": None},
        {"text": "Veiller plus tard le soir", "image": None},
        {"text": "Inviter un copain à dormir", "image": None},
        {"text": "Choisir le film familial", "image": None},
        {"text": "Avoir le droit de sauter le bain", "image": None},
        {"text": "Manger son dessert préféré", "image": None},
        {"text": "Choisir l'activité du week-end", "image": None},
        {"text": "Recevoir un petit jouet/livre surprise", "image": None},
        {"text": "Avoir du temps d'écran bonus", "image": None},
        {"text": "Dormir dans le lit des parents", "image": None},
        # Temps privilégié (11-20)
        {"text": "Une sortie spéciale parent-enfant au choix", "image": None},
        {"text": "Jouer à son jeu préféré avec papa/maman", "image": None},
        {"text": "Lire une histoire de plus au coucher", "image": None},
        {"text": "Faire une activité créative avec les parents", "image": None},
        {"text": "Aller au parc/aire de jeux", "image": None},
        {"text": "Choisir la musique en voiture", "image": None},
        {"text": "Faire des crêpes/gaufres ensemble", "image": None},
        {"text": "Session câlins et chatouilles", "image": None},
        {"text": "Pique-niquer dans le salon", "image": None},
        {"text": "Construire une cabane ensemble", "image": None},
        # Exemptions rigolotes (21-30)
        {"text": "Passer son tour pour ranger sa chambre", "image": None},
        {"text": "Choisir ses vêtements (même bizarres)", "image": None},
        {"text": "Manger avec les doigts", "image": None},
        {"text": "Ne pas finir ses légumes", "image": None},
        {"text": "Avoir le droit de faire du bruit", "image": None},
        {"text": "Porter son pyjama toute la journée", "image": None},
        {"text": "Manger le petit-déjeuner au lit", "image": None},
        {"text": "Sauter la routine des devoirs", "image": None},
        {"text": "Avoir un goûter spécial", "image": None},
        {"text": "Choisir son petit-déjeuner", "image": None},
        # Récompenses spéciales (31-40)
        {"text": "Recevoir une médaille/diplôme fait maison", "image": None},
        {"text": "Être le 'chef de famille' pour la journée", "image": None},
        {"text": "Organiser une chasse au trésor par les parents", "image": None},
        {"text": "Faire une soirée pyjama dans le salon", "image": None},
        {"text": "Avoir un jour 'oui' (parents disent oui à tout le raisonnable)", "image": None},
        {"text": "Recevoir des autocollants collector", "image": None},
        {"text": "Préparer un gâteau avec maman/papa", "image": None},
        {"text": "Aller chercher une surprise au magasin", "image": None},
        {"text": "Avoir une journée 'bon élève' sans corvées", "image": None},
        {"text": "Organiser une mini-fête à la maison", "image": None}
    ]
    
    # Grille Couple (40 récompenses par défaut)
    default_rewards_couple = [
        # Romantique et détente (1-10)
        {"text": "Massage complet", "image": None},
        {"text": "Petit-déjeuner au lit préparé par l'autre", "image": None},
        {"text": "Soirée spa maison", "image": None},
        {"text": "Bain aux chandelles préparé", "image": None},
        {"text": "Être dispensé de cuisine", "image": None},
        {"text": "Dîner aux chandelles maison", "image": None},
        {"text": "Soirée cinéma avec snacks préférés", "image": None},
        {"text": "Grasse matinée sans réveil", "image": None},
        {"text": "Avoir la salle de bain en premier", "image": None},
        {"text": "Choisir la température de la chambre", "image": None},
        # Temps de qualité (11-20)
        {"text": "Date night planifiée et payée par l'autre", "image": None},
        {"text": "Week-end sans parler de tâches domestiques", "image": None},
        {"text": "Soirée jeux à deux", "image": None},
        {"text": "Promenade main dans la main", "image": None},
        {"text": "Danser ensemble dans le salon", "image": None},
        {"text": "Session photo couple rigolote", "image": None},
        {"text": "Écrire une lettre d'amour", "image": None},
        {"text": "Regarder le lever/coucher de soleil ensemble", "image": None},
        {"text": "Pique-niquer à deux", "image": None},
        {"text": "Soirée karaoké privée", "image": None},
        # Privilèges du quotidien (21-30)
        {"text": "Choisir tous les films/séries", "image": None},
        {"text": "Contrôle total de la télécommande", "image": None},
        {"text": "Avoir le côté du lit préféré", "image": None},
        {"text": "Ne pas faire la vaisselle", "image": None},
        {"text": "Être servi son café/thé au réveil", "image": None},
        {"text": "Choisir la musique de la maison", "image": None},
        {"text": "Avoir la couette entière", "image": None},
        {"text": "Dormir sans être réveillé", "image": None},
        {"text": "Choisir les sorties", "image": None},
        {"text": "Avoir le dernier mot sur la déco", "image": None},
        # Fun et coquin (31-40)
        {"text": "Strip poker version corvées", "image": None},
        {"text": "Massage sensuel aux huiles", "image": None},
        {"text": "Soirée costumée à deux", "image": None},
        {"text": "Jeu de vérité ou action", "image": None},
        {"text": "Chasse au trésor coquine dans la maison", "image": None},
        {"text": "Soirée dégustation (vin, fromage, chocolat)", "image": None},
        {"text": "Cours de danse improvisé", "image": None},
        {"text": "Karaoké love songs", "image": None},
        {"text": "Session photos boudoir amateur", "image": None},
        {"text": "Nuit d'hôtel ou escapade surprise", "image": None}
    ]
    
    # Grille Coloc (40 récompenses par défaut)
    default_rewards_coloc = [
        # Privilèges domestiques (1-10)
        {"text": "Passer son tour de ménage", "image": None},
        {"text": "Choisir la température de l'appart", "image": None},
        {"text": "Avoir la salle de bain en premier", "image": None},
        {"text": "Utiliser la machine à laver en priorité", "image": None},
        {"text": "Avoir le meilleur spot de parking/rangement vélo", "image": None},
        {"text": "Choisir l'organisation du frigo", "image": None},
        {"text": "Ne pas sortir les poubelles", "image": None},
        {"text": "Être dispensé de vaisselle", "image": None},
        {"text": "Avoir la télécommande TV", "image": None},
        {"text": "Choisir le parfum des produits ménagers", "image": None},
        # Nourriture et cuisine (11-20)
        {"text": "Les autres préparent ton plat préféré", "image": None},
        {"text": "Avoir le droit de finir les restes premium", "image": None},
        {"text": "Se faire livrer un resto aux frais des autres", "image": None},
        {"text": "Avoir l'étagère du frigo la plus accessible", "image": None},
        {"text": "Choisir les courses", "image": None},
        {"text": "Recevoir un dessert surprise", "image": None},
        {"text": "Ne pas cuisiner", "image": None},
        {"text": "Avoir le droit aux meilleurs snacks", "image": None},
        {"text": "Organiser un apéro payé par les colocs", "image": None},
        {"text": "Choisir le resto pour la prochaine sortie groupe", "image": None},
        # Espace personnel (21-30)
        {"text": "Monopoliser le salon pour une soirée", "image": None},
        {"text": "Mettre sa musique à fond", "image": None},
        {"text": "Organiser une soirée avec ses amis", "image": None},
        {"text": "Avoir la paix absolue", "image": None},
        {"text": "Choisir la déco des espaces communs", "image": None},
        {"text": "Utiliser l'espace commun pour son hobby", "image": None},
        {"text": "Avoir le meilleur siège du salon", "image": None},
        {"text": "Faire du bruit sans plainte possible", "image": None},
        {"text": "Occuper la cuisine pour un projet culinaire", "image": None},
        {"text": "Réorganiser un espace commun à son goût", "image": None},
        # Social et fun (31-40)
        {"text": "Obliger les colocs à faire une soirée jeux", "image": None},
        {"text": "Organiser une soirée thématique", "image": None},
        {"text": "Choisir le film de la soirée coloc", "image": None},
        {"text": "Imposer une journée pyjama collectif", "image": None},
        {"text": "Recevoir un trophée/médaille ridicule", "image": None},
        {"text": "Avoir un titre honorifique affiché ('Maître du balai')", "image": None},
        {"text": "Les colocs doivent porter un accessoire ridicule", "image": None},
        {"text": "Organiser un concours débile", "image": None},
        {"text": "Créer une règle absurde", "image": None},
        {"text": "Avoir un 'joker silence' (faire taire les colocs quand on veut)", "image": None}
    ]
    
    # Charger les récompenses personnalisées si elles existent
    c.execute("SELECT rewards_json FROM custom_rewards WHERE house_id=? AND house_type=?", (house_id, house_type))
    custom_rewards_row = c.fetchone()
    
    _dbg(f"[DEBUG] Recherche custom_rewards: house_id={house_id}, house_type={house_type}")
    _dbg(f"[DEBUG] custom_rewards_row trouvé: {custom_rewards_row is not None}")
    
    if custom_rewards_row:
        # Utiliser les récompenses personnalisées
        custom_rewards_list = json.loads(custom_rewards_row[0])
        rewards = [{"text": reward, "image": None} for reward in custom_rewards_list]
        _dbg(f"[DEBUG] Utilisation de {len(rewards)} récompenses personnalisées")
    else:
        # Utiliser les récompenses par défaut selon le type de foyer
        if house_type == 'couple':
            rewards = default_rewards_couple
            _dbg(f"[DEBUG] Utilisation des récompenses par défaut COUPLE")
        elif house_type == 'coloc':
            rewards = default_rewards_coloc
            _dbg(f"[DEBUG] Utilisation des récompenses par défaut COLOC")
        else:
            rewards = default_rewards_family
            _dbg(f"[DEBUG] Utilisation des récompenses par défaut FAMILLE")
    
    reward = random.choice(rewards)
    reward_text = reward["text"]
    reward_image = reward["image"]
    
    # S'assurer que la table mystery_rewards existe
    c.execute("""
    CREATE TABLE IF NOT EXISTS mystery_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        house_id INTEGER NOT NULL,
        reward_text TEXT NOT NULL,
        won_date DATE DEFAULT CURRENT_DATE,
        used INTEGER DEFAULT 0,
        used_date DATE,
        FOREIGN KEY(user_email) REFERENCES users(email),
        FOREIGN KEY(house_id) REFERENCES houses(id)
    )
    """)
    
    # Enregistrer la case ouverte avec la semaine
    # MODE TEST: On supprime d'abord l'ancienne entrée si elle existe
    try:
        c.execute("DELETE FROM reward_boxes WHERE house_id=? AND box_number=?", (house_id, box_number))
    except:
        pass
    
    try:
        c.execute("""
            INSERT INTO reward_boxes (house_id, box_number, reward_text, opened_by, week_start)
            VALUES (?, ?, ?, ?, ?)
        """, (house_id, box_number, reward_text, session['user'], start_of_week))
        
        # Enregistrer la récompense dans les récompenses du joueur
        _dbg(f"[DEBUG] Insertion dans mystery_rewards: user={session['user']}, house={house_id}, reward={reward_text}")
        c.execute("""
            INSERT INTO mystery_rewards (user_email, house_id, reward_text, won_date, used)
            VALUES (?, ?, ?, date('now'), 0)
        """, (session['user'], house_id, reward_text))
        
        conn.commit()
        _dbg(f"[DEBUG] Récompense enregistrée avec succès!")
    except Exception as e:
        conn.close()
        _dbg(f"[ERROR] Erreur lors de l'insertion: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur base de données: {str(e)}'}), 500
    
    conn.close()
    
    # Récupérer le nom de l'utilisateur
    user_name = session.get('user_name', '')
    if not user_name:
        conn2 = get_db_connection()
        c2 = conn2.cursor()
        c2.execute("SELECT name FROM users WHERE email=?", (session['user'],))
        name_row = c2.fetchone()
        user_name = name_row[0] if name_row and name_row[0] else 'Champion'
        conn2.close()
    
    response = {'success': True, 'reward': reward_text, 'winner_name': user_name}
    if reward_image:
        response['image'] = reward_image
    
    return jsonify(response)


@app.route('/mes_recompenses')
def mes_recompenses():
    """Page pour voir les récompenses mystère de tous les joueurs de la maison"""
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_row = c.fetchone()
    if not house_row or not house_row[0]:
        conn.close()
        flash("Vous devez rejoindre une maison", "warning")
        return redirect(url_for('menu'))
    
    house_id = house_row[0]
    
    _dbg(f"[DEBUG mes_recompenses] house_id={house_id}, user={session['user']}")
    
    # ===== UTILISER get_house_players_points() pour garantir les mêmes avatars que le menu =====
    players_from_menu = get_house_players_points(house_id)
    
    # Construire directement la liste players_data depuis get_house_players_points
    players_data = []
    for p in players_from_menu:
        player_email = p.get('email')
        player_name = p.get('name', '')
        
        # Récompenses disponibles de ce joueur
        c.execute("""
            SELECT id, reward_text, won_date
            FROM mystery_rewards
            WHERE user_email=? AND used=0
            ORDER BY id DESC
        """, (player_email,))
        
        available = []
        for r in c.fetchall():
            available.append({
                'id': r[0],
                'text': r[1],
                'date': r[2]
            })
        
        _dbg(f"[DEBUG] Joueur {player_name} ({player_email}): {len(available)} récompenses disponibles")
        _dbg(f"[DEBUG]   avatar={p.get('avatar')}, file={p.get('avatar_file')}, url={p.get('avatar_url')}, style={p.get('avatar_style')}")
        
        # Récompenses utilisées de ce joueur
        c.execute("""
            SELECT id, reward_text, won_date, used_date
            FROM mystery_rewards
            WHERE user_email=? AND used=1
            ORDER BY used_date DESC
        """, (player_email,))
        
        used = []
        for r in c.fetchall():
            used.append({
                'id': r[0],
                'text': r[1],
                'won_date': r[2],
                'used_date': r[3]
            })
        
        players_data.append({
            'email': player_email,
            'name': player_name,
            'avatar': p.get('avatar'),
            'avatar_file': p.get('avatar_file'),
            'avatar_url': p.get('avatar_url'),
            'avatar_style': p.get('avatar_style', 'adventurer'),
            'available_rewards': available,
            'used_rewards': used,
            'is_current_user': player_email == session['user']
        })
    
    conn.close()
    
    response = make_response(render_template('rewards_grid.html',
                         players=players_data,
                         current_user=session['user'],
                         hide_header=True))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/use_reward/<int:reward_id>', methods=['POST'])
def use_reward(reward_id):
    """Marquer une récompense comme utilisée"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'}), 401
    
    _dbg(f"[DEBUG use_reward] reward_id={reward_id}, user={session['user']}")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Vérifier que la récompense appartient à l'utilisateur
    c.execute("""
        SELECT id FROM mystery_rewards
        WHERE id=? AND user_email=? AND used=0
    """, (reward_id, session['user']))
    
    reward_row = c.fetchone()
    _dbg(f"[DEBUG] Récompense trouvée: {reward_row is not None}")
    
    if not reward_row:
        conn.close()
        return jsonify({'success': False, 'message': 'Récompense non trouvée'}), 404
    
    # Marquer comme utilisée
    c.execute("""
        UPDATE mystery_rewards
        SET used=1, used_date=date('now')
        WHERE id=?
    """, (reward_id,))
    
    rows_affected = c.rowcount
    _dbg(f"[DEBUG] Lignes modifiées: {rows_affected}")
    
    conn.commit()
    conn.close()
    
    _dbg(f"[DEBUG] Récompense {reward_id} marquée comme utilisée avec succès")
    
    return jsonify({'success': True})


@app.route('/buy_reward/<int:reward_id>')
def buy_reward(reward_id):
    # Fonctionnalité temporairement désactivée
    return redirect(url_for('menu'))
    
    if 'user' not in session:
        flash("Connecte-toi pour acheter une récompense", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()

    # Vérifier les points et si l'utilisateur a déjà acheté la récompense aujourd'hui
    c.execute("SELECT points FROM users WHERE email=?", (session['user'],))
    points = c.fetchone()[0]

    c.execute("SELECT cost FROM rewards WHERE id=?", (reward_id,))
    cost = c.fetchone()[0]

    today = date.today().isoformat()
    c.execute("SELECT * FROM user_rewards WHERE user_email=? AND reward_id=? AND purchased_date=?", (session['user'], reward_id, today))
    already_bought_today = c.fetchone()

    if already_bought_today:
        flash("Tu as déjà obtenu cette récompense aujourd'hui. Reviens demain !", "info")
    elif points < cost:
        flash("Pas assez de points pour acheter cette récompense.", "danger")
    else:
        # Déduire les points et ajouter la récompense avec la date d'aujourd'hui
        c.execute("UPDATE users SET points = points - ? WHERE email=?", (cost, session['user']))
        c.execute("INSERT INTO user_rewards (user_email, reward_id, purchased_date) VALUES (?, ?, ?)", (session['user'], reward_id, today))
        conn.commit()
        flash("Récompense achetée !", "success")

    conn.close()
    return redirect(url_for('rewards'))


# ===============================
# NOUVELLES ROUTES CLEANBEAT
# ===============================

@app.route('/gifts')
def gifts():
    """Grille de cadeaux Dust - débloquée le dimanche matin"""
    if 'user' not in session:
        flash("🔐 Connecte-toi pour voir tes cadeaux !", "warning")
        return redirect(url_for('signup_email'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer house_id de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_id = c.fetchone()[0]
    
    # ⚡ Vérifier et effectuer la réinitialisation hebdomadaire des statistiques si nécessaire
    check_weekly_reset(house_id, conn)
    
    # Récupérer les informations de la maison (utilise 'house_name' si présent, sinon 'name')
    c.execute("SELECT code, name, house_name FROM houses WHERE id=?", (house_id,))
    house_info = c.fetchone()
    house_code = house_info[0]
    # colonne 2 = house_name, colonne 1 = name
    house_name = house_info[2] if house_info and house_info[2] else (house_info[1] if house_info and house_info[1] else None)
    
    # Récupérer tous les joueurs
    players = get_house_players_points(house_id)
    
    # Vérifier si c'est dimanche après 6h du matin
    from datetime import datetime
    now = datetime.now()
    is_sunday = now.weekday() == 6  # 6 = dimanche
    is_morning_unlock = now.hour >= 6
    can_open_gifts = is_sunday and is_morning_unlock
    
    # Liste des cadeaux prédéfinis
    default_gifts = [
        {'id': 1, 'name': '🍽️ Dîner au restaurant', 'revealed': False, 'description': 'Une soirée romantique au restaurant de votre choix !'},
        {'id': 2, 'name': '💆 Massage 30 min', 'revealed': False, 'description': 'Un moment de détente bien mérité !'},
        {'id': 3, 'name': '💐 Bouquet de fleurs', 'revealed': False, 'description': 'De jolies fleurs pour égayer la maison !'},
        {'id': 4, 'name': '📺 Choisir la série', 'revealed': False, 'description': 'Le pouvoir de choisir ce qu\'on regarde ce soir !'},
        {'id': 5, 'name': '🛏️ Petit déj au lit', 'revealed': False, 'description': 'Un réveil en douceur le dimanche matin !'},
        {'id': 6, 'name': '🧖‍♀️ Journée spa', 'revealed': False, 'description': 'Une journée complète de relaxation !'},
        {'id': 7, 'name': '🎬 Sortie cinéma', 'revealed': False, 'description': 'Une soirée ciné avec pop-corn !'},
        {'id': 8, 'name': '🏖️ Week-end surprise', 'revealed': False, 'description': 'Une escapade mystère de 2 jours !'},
        {'id': 9, 'name': '🕯️ Dîner aux chandelles', 'revealed': False, 'description': 'Un repas romantique à la maison !'}
    ]
    
    # Récupérer les cadeaux révélés depuis la base de données
    c.execute("SELECT gift_id, revealed_by, revealed_date FROM revealed_gifts WHERE house_id=?", (house_id,))
    revealed_data = {row[0]: {'revealed_by': row[1], 'revealed_date': row[2]} for row in c.fetchall()}
    
    # Mettre à jour les cadeaux avec les données révélées
    for gift in default_gifts:
        if gift['id'] in revealed_data:
            gift['revealed'] = True
            gift['revealed_by'] = revealed_data[gift['id']]['revealed_by']
            gift['revealed_date'] = revealed_data[gift['id']]['revealed_date']
    
    conn.close()
    
    return render_template('gifts.html', 
                         gifts=default_gifts, 
                         can_open_gifts=can_open_gifts,
                         players=players, 
                         house_code=house_code,
                         house_name=house_name)

@app.route('/reveal_gift/<int:gift_id>')
def reveal_gift(gift_id):
    """Révéler un cadeau"""
    if 'user' not in session:
        return redirect(url_for('signup_email'))
    
    # Vérifier si c'est dimanche après 6h du matin
    from datetime import datetime
    now = datetime.now()
    is_sunday = now.weekday() == 6
    is_morning_unlock = now.hour >= 6
    can_open_gifts = is_sunday and is_morning_unlock
    
    if not can_open_gifts:
        flash("🚫 Les cadeaux ne peuvent être ouverts que le dimanche à partir de 6h du matin ! ⏰", "warning")
        return redirect(url_for('gifts'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer house_id
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_id = c.fetchone()[0]
    
    # Vérifier si le cadeau n'est pas déjà révélé
    c.execute("SELECT * FROM revealed_gifts WHERE house_id=? AND gift_id=?", (house_id, gift_id))
    if c.fetchone():
        flash("🎁 Ce cadeau a déjà été ouvert ! Choisissez-en un autre ! ✨", "info")
        conn.close()
        return redirect(url_for('gifts'))
    
    # Révéler le cadeau
    current_date = datetime.now().isoformat()
    c.execute("INSERT INTO revealed_gifts (house_id, gift_id, revealed_by, revealed_date) VALUES (?, ?, ?, ?)", 
              (house_id, gift_id, session['user'], current_date))
    conn.commit()
    conn.close()
    
    # Messages de félicitations
    gift_names = {
        1: '🍽️ Dîner au restaurant',
        2: '💆 Massage 30 min', 
        3: '💐 Bouquet de fleurs',
        4: '📺 Choisir la série',
        5: '🛏️ Petit déj au lit',
        6: '🧖‍♀️ Journée spa',
        7: '🎬 Sortie cinéma',
        8: '🏖️ Week-end surprise',
        9: '🕯️ Dîner aux chandelles'
    }
    
    gift_name = gift_names.get(gift_id, 'Cadeau mystère')
    flash(f"🎊 FÉLICITATIONS ! Vous avez gagné : {gift_name} ! 🎉 Profitez bien ! ✨", "success")
    
    return redirect(url_for('gifts'))

@app.route('/chat')
def chat():
    """Chat/messagerie entre partenaires (placeholder)"""
    if 'user' not in session:
        flash("🔐 Connecte-toi pour accéder au chat !", "warning")
        return redirect(url_for('signup_email'))
    
    flash("💬 Chat en cours de développement ! Bientôt vous pourrez échanger avec votre partenaire ! 🚀", "info")
    return redirect(url_for('menu'))


# Login
@app.route('/login', methods=['GET','POST'])
def login():
    # La page de login ne doit jamais être protégée par une vérification de session !
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        next_code = request.form.get('next_code', '').strip().upper() or request.args.get('next_code', '').strip().upper()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT password, registration_step, avatar, avatar_file FROM users WHERE email=?", (email,))
        user = c.fetchone()
        if user and check_password_hash(user[0], password):
            session.permanent = True
            session['user'] = email
            _log_login(email)

            # Si le joueur a un code d'invitation, le rattacher à la maison
            if next_code:
                c.execute("SELECT id FROM houses WHERE code=?", (next_code,))
                house_row = c.fetchone()
                if house_row:
                    c.execute("UPDATE users SET house_id=? WHERE email=?", (house_row[0], email))
                    conn.commit()
                    conn.close()
                    flash("🏠 Tu as rejoint la maison avec succès !", "success")
                    return redirect(url_for('menu'))

            conn.close()

            # Vérifier si l'utilisateur est au milieu d'une inscription non terminée
            registration_step = user[1] or ''
            avatar = user[2] or ''
            avatar_file = user[3] or ''

            # Rediriger vers create_profile seulement si l'inscription n'est pas terminée
            if registration_step == 'email_signup' and not avatar and not avatar_file:
                flash("✨ Complète ton profil pour commencer !", "info")
                return redirect(url_for('create_profile'))

            return redirect(url_for('menu'))
        else:
            flash("Email ou mot de passe incorrect", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Déconnecté.", "success")
    return redirect(url_for('login'))


# ─── Route debug temporaire (à supprimer après usage) ───────────────────────
@app.route('/admin_clean_users')
def admin_clean_users():
    key = request.args.get('key', '')
    if key != 'dust2026admin':
        return "Accès refusé", 403
    action = request.args.get('action', '')
    email_keep = request.args.get('email', '').strip().lower()
    new_pwd = request.args.get('pwd', '').strip()
    conn = get_db_connection()
    c = conn.cursor()
    msg = ""
    # Action : garder uniquement un compte, supprimer tous les autres RÉELS (pas les enfants)
    if action == 'keeponly' and email_keep:
        c.execute("DELETE FROM users WHERE email != ? AND (is_child_account IS NULL OR is_child_account = 0)", (email_keep,))
        conn.commit()
        msg = f"✅ Tous les comptes adultes supprimés sauf {email_keep}"
    # Action : réinitialiser le mot de passe d'un email
    if action == 'resetpwd' and email_keep and new_pwd:
        hashed = generate_password_hash(new_pwd)
        c.execute("UPDATE users SET password=? WHERE email=?", (hashed, email_keep))
        conn.commit()
        msg = f"✅ Mot de passe réinitialisé pour {email_keep}"
    # Action : supprimer un compte par email
    if action == 'delete' and email_keep:
        c.execute("DELETE FROM users WHERE email=?", (email_keep,))
        conn.commit()
        msg = f"🗑️ Compte supprimé : {email_keep}"
    # Lister les 30 derniers comptes
    c.execute("SELECT id, email, name, registration_step, house_id FROM users ORDER BY id DESC LIMIT 30")
    rows = c.fetchall()
    conn.close()
    html = f"<h2>Comptes (30 derniers) {msg}</h2><table border=1>"
    html += "<tr><th>ID</th><th>Email</th><th>Nom</th><th>Step</th><th>House</th><th>Actions</th></tr>"
    for r in rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td>"
        html += f"<td><a href='?key=dust2026admin&action=delete&email={r[1]}' onclick=\"return confirm('Supprimer ?')\">🗑️ Supprimer</a></td></tr>"
    html += "</table>"
    html += "<br><b>⭐ Garder uniquement un compte (supprimer tous les autres) :</b><br>"
    html += "<form method=get>Email à garder: <input name=email style='width:250px'> <input type=hidden name=key value=dust2026admin> <input type=hidden name=action value=keeponly> <input type=submit value='Garder uniquement cet email' onclick=\"return confirm('Supprimer TOUS les autres comptes adultes ?')\"></form>"
    html += "<br><b>Réinitialiser un mot de passe :</b><br>"
    html += "<form method=get>Email: <input name=email style='width:250px'> Nouveau pwd: <input name=pwd> <input type=hidden name=key value=dust2026admin> <input type=hidden name=action value=resetpwd> <input type=submit value='Réinitialiser'></form>"
    return html

# ─── Dashboard bêta-testeurs ────────────────────────────────────────────────
@app.route('/admin_beta')
def admin_beta():
    key = request.args.get('key', '')
    if key != 'dust2026admin':
        return "Accès refusé", 403

    conn = get_db_connection()
    c = conn.cursor()
    errors = []

    # Tous les utilisateurs inscrits (hors comptes enfants)
    try:
        c.execute("""
            SELECT u.email, u.name, u.phone, u.registration_step,
                   MIN(ct.completed_at) as premiere_activite
            FROM users u
            LEFT JOIN completed_tasks ct ON ct.user_email = u.email
            WHERE u.is_child_account IS NULL OR u.is_child_account = 0
            GROUP BY u.id, u.email, u.name, u.phone, u.registration_step
            ORDER BY u.id DESC
        """)
        users_rows = c.fetchall()
    except Exception as e:
        users_rows = []
        errors.append(f"users: {e}")

    # Connexions par jour (30 derniers jours)
    try:
        c.execute("""
            SELECT DATE(logged_at) as day, COUNT(*) as cnt
            FROM login_logs
            GROUP BY DATE(logged_at)
            ORDER BY day DESC
            LIMIT 30
        """)
        daily_rows = c.fetchall()
    except Exception as e:
        daily_rows = []
        errors.append(f"login_logs jour: {e}")

    # Connexions par utilisateur (top 50)
    try:
        c.execute("""
            SELECT email, COUNT(*) as cnt, MAX(logged_at) as last_login
            FROM login_logs
            GROUP BY email
            ORDER BY cnt DESC
            LIMIT 50
        """)
        user_logins = c.fetchall()
    except Exception as e:
        user_logins = []
        errors.append(f"login_logs user: {e}")

    # Activité : tâches validées par joueur (30 derniers jours)
    try:
        c.execute("""
            SELECT user_email, COUNT(*) as nb_taches, SUM(points) as total_pts,
                   MAX(completed_at) as derniere_action
            FROM completed_tasks
            WHERE completed_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            GROUP BY user_email
            ORDER BY nb_taches DESC
            LIMIT 50
        """)
        activity_rows = c.fetchall()
    except Exception:
        try:
            c.execute("""
                SELECT user_email, COUNT(*) as nb_taches, SUM(points) as total_pts,
                       MAX(completed_at) as derniere_action
                FROM completed_tasks
                WHERE DATE(completed_at) >= DATE('now','-30 days')
                GROUP BY user_email
                ORDER BY nb_taches DESC
                LIMIT 50
            """)
            activity_rows = c.fetchall()
        except Exception as e2:
            activity_rows = []
            errors.append(f"activity: {e2}")

    # 20 dernières tâches validées (toutes personnes confondues)
    try:
        c.execute("""
            SELECT user_email, task_name, points, completed_at
            FROM completed_tasks
            ORDER BY completed_at DESC
            LIMIT 20
        """)
        recent_tasks = c.fetchall()
    except Exception as e:
        recent_tasks = []
        errors.append(f"recent_tasks: {e}")

    conn.close()

    total_users = len(users_rows)
    total_logins = sum(r[1] for r in daily_rows)
    total_tasks = sum(r[1] for r in activity_rows)

    css = """
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #e94560; } h2 { color: #0f3460; background:#16213e; padding:8px; border-radius:6px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
        th { background: #0f3460; color: #fff; padding: 8px 12px; text-align: left; }
        td { padding: 6px 12px; border-bottom: 1px solid #333; }
        tr:hover td { background: #1a2a4a; }
        .stat { display: inline-block; background: #16213e; border: 2px solid #0f3460;
                padding: 15px 25px; margin: 10px; border-radius: 10px; text-align: center; }
        .stat h3 { margin: 0; font-size: 2em; color: #e94560; }
        .stat p { margin: 5px 0 0; color: #aaa; }
        .err { background:#5a1a1a; padding:8px; border-radius:4px; margin:5px 0; font-size:0.85em; }
    </style>
    """

    html = f"{css}<h1>📊 Dashboard bêta-testeurs CleanBeat</h1>"
    if errors:
        for err in errors:
            html += f"<div class='err'>⚠️ {err}</div>"
    html += f"""
    <div>
        <div class='stat'><h3>{total_users}</h3><p>Utilisateurs inscrits</p></div>
        <div class='stat'><h3>{total_logins}</h3><p>Connexions (30j)</p></div>
        <div class='stat'><h3>{total_tasks}</h3><p>Tâches validées (30j)</p></div>
    </div>
    """

    html += "<h2>👥 Utilisateurs inscrits</h2>"
    html += "<table><tr><th>#</th><th>Email</th><th>Nom</th><th>Téléphone</th><th>1ère activité</th><th>Step</th></tr>"
    for i, r in enumerate(users_rows, 1):
        email, name, phone, step, premiere = r
        date_str = str(premiere)[:16] if premiere else '-'
        html += f"<tr><td>{i}</td><td>{email or '-'}</td><td>{name or '-'}</td><td>{phone or '-'}</td><td>{date_str}</td><td>{step or '-'}</td></tr>"
    html += "</table>"

    html += "<h2>🏃 Activité des joueurs (30 derniers jours)</h2>"
    html += "<table><tr><th>Email</th><th>Tâches validées</th><th>Points gagnés</th><th>Dernière action</th></tr>"
    for r in activity_rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{int(r[2] or 0)}</td><td>{str(r[3])[:16] if r[3] else '-'}</td></tr>"
    html += "</table>"

    html += "<h2>⚡ 20 dernières tâches validées</h2>"
    html += "<table><tr><th>Joueur</th><th>Tâche</th><th>Points</th><th>Date</th></tr>"
    for r in recent_tasks:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{str(r[3])[:16] if r[3] else '-'}</td></tr>"
    html += "</table>"

    html += "<h2>📅 Connexions par jour</h2>"
    html += "<table><tr><th>Date</th><th>Nb connexions</th></tr>"
    for r in daily_rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td></tr>"
    html += "</table>"

    html += "<h2>🔥 Connexions par utilisateur</h2>"
    html += "<table><tr><th>Email</th><th>Nb connexions</th><th>Dernière connexion</th></tr>"
    for r in user_logins:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{str(r[2])[:16] if r[2] else '-'}</td></tr>"
    html += "</table>"

    return html


# ─── Mot de passe oublié ────────────────────────────────────────────────────
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    reset_link = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT email FROM users WHERE email=?", (email,))
        user = c.fetchone()
        if user:
            # Supprimer les anciens tokens non utilisés pour cet email
            c.execute("DELETE FROM password_reset_tokens WHERE email=? AND used=0", (email,))
            # Générer un token sécurisé valable 1 heure
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
            c.execute("INSERT INTO password_reset_tokens (token, email, expires_at, used) VALUES (?, ?, ?, 0)",
                      (token, email, expires_at))
            conn.commit()
            conn.close()
            # Construire le lien (avec l'hôte actuel)
            reset_link = url_for('reset_password', token=token, _external=True)
        else:
            conn.close()
            # Message neutre pour ne pas révéler si l'email existe
            reset_link = '__not_found__'
    return render_template('forgot_password.html', reset_link=reset_link)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT email, expires_at, used FROM password_reset_tokens WHERE token=?", (token,))
    row = c.fetchone()

    if not row:
        conn.close()
        flash("Lien invalide ou expiré.", "danger")
        return redirect(url_for('login'))

    email, expires_at, used = row
    if used:
        conn.close()
        flash("Ce lien a déjà été utilisé. Fais une nouvelle demande.", "warning")
        return redirect(url_for('forgot_password'))

    if datetime.now() > datetime.fromisoformat(expires_at):
        conn.close()
        flash("Ce lien a expiré (valable 1h). Fais une nouvelle demande.", "warning")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        if len(new_password) < 8:
            conn.close()
            flash("Le mot de passe doit contenir au moins 8 caractères.", "danger")
            return render_template('reset_password.html', token=token)
        # Mettre à jour le mot de passe
        hashed = generate_password_hash(new_password)
        c.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
        # Invalider le token
        c.execute("UPDATE password_reset_tokens SET used=1 WHERE token=?", (token,))
        conn.commit()
        conn.close()
        flash("✅ Mot de passe mis à jour ! Tu peux te connecter.", "success")
        return redirect(url_for('login'))

    conn.close()
    return render_template('reset_password.html', token=token, email=email)
# ─────────────────────────────────────────────────────────────────────────────


# Page Mon Profil (glassmorphisme)
@app.route('/profile')
def profile():
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer les infos utilisateur
    c.execute("SELECT name, email, avatar, avatar_file, house_id, avatar_url, avatar_style FROM users WHERE email=?", (session['user'],))
    user = c.fetchone()
    
    if not user:
        conn.close()
        flash("Utilisateur non trouvé", "danger")
        return redirect(url_for('login'))
    
    user_name, user_email, user_avatar, user_photo, house_id, user_avatar_url, user_avatar_style = user
    
    # Récupérer les infos de la maison
    house_name = ''
    house_code = ''
    if house_id:
        c.execute("SELECT house_name, code FROM houses WHERE id=?", (house_id,))
        house = c.fetchone()
        if house:
            house_name, house_code = house
    
    conn.close()
    
    return render_template('profile.html',
                           user_name=user_name,
                           user_email=user_email,
                           user_avatar=user_avatar,
                           user_photo=user_photo,
                           user_avatar_url=user_avatar_url,
                           user_avatar_style=user_avatar_style,
                           house_name=house_name,
                           house_code=house_code)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    name = request.form.get('name', '').strip().capitalize()
    avatar = request.form.get('avatar', '').strip()
    avatar_style = request.form.get('avatar_style', 'lorelei').strip()
    photo_data = request.form.get('photo_data')
    house_name_input = request.form.get('house_name', '').strip()
    
    import sys
    _dbg(f"🔍 UPDATE PROFILE: name={name}, avatar={avatar}, style={avatar_style}")
    sys.stdout.flush()
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # 📛 Récupérer l'ancien nom AVANT la mise à jour (pour propager le changement)
    old_name = None
    profile_house_id = None
    if name:
        c.execute("SELECT name, house_id FROM users WHERE email=?", (session['user'],))
        old_row = c.fetchone()
        old_name = old_row[0] if old_row and old_row[0] else None
        profile_house_id = old_row[1] if old_row else None
    
    update_fields = []
    update_values = []
    
    # Mettre à jour le nom
    if name:
        update_fields.append("name=?")
        update_values.append(name)
        session['user_name'] = name
        if 'name' in session:
            session['name'] = name
    
    # Gérer la photo uploadée (priorité maximale) — stockage data URI en DB
    if photo_data and photo_data.startswith('data:image'):
        photo_data_uri = save_photo_from_base64(photo_data)
        if photo_data_uri:
            update_fields.extend(["avatar_url=?", "avatar_file=?", "avatar=?", "avatar_style=?"])
            update_values.extend([photo_data_uri, '', '', ''])
            session['user_avatar_url'] = photo_data_uri
            _dbg(f"✅ Photo stockée en DB (data URI, {len(photo_data_uri)} chars)")
    
    # Gérer l'avatar si pas de photo
    elif avatar:
        _dbg(f"   📝 Traitement avatar: '{avatar}'")
        is_file = avatar.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        is_emoji = len(avatar) <= 4 and any(ord(c) > 127 for c in avatar)
        is_dicebear = not is_file and not is_emoji
        _dbg(f"   📋 Type détecté: file={is_file}, emoji={is_emoji}, dicebear={is_dicebear}")
        
        if is_file:
            update_fields.extend(["avatar_file=?", "avatar=?", "avatar_url=?", "avatar_style=?"])
            update_values.extend([avatar, '', '', ''])
            session['user_avatar'] = avatar
            _dbg(f"✅ Fichier: {avatar}")
            
        elif is_emoji:
            update_fields.extend(["avatar=?", "avatar_file=?", "avatar_url=?", "avatar_style=?"])
            update_values.extend([avatar, '', '', ''])
            session['user_avatar'] = avatar
            _dbg(f"✅ Emoji: {avatar}")
            
        else:  # is_dicebear
            dicebear_url = f"https://api.dicebear.com/7.x/{avatar_style}/svg?seed={avatar}"
            update_fields.extend(["avatar=?", "avatar_url=?", "avatar_style=?", "avatar_file=?"])
            update_values.extend([avatar, dicebear_url, avatar_style, ''])
            session['user_avatar'] = avatar
            _dbg(f"✅ DiceBear: seed={avatar}, style={avatar_style}, url={dicebear_url}")
            _dbg(f"   🔧 update_fields: {update_fields}")
            _dbg(f"   🔧 update_values: {update_values}")
            sys.stdout.flush()
        
        if 'user_photo' in session:
            del session['user_photo']
    
    # Toujours marquer le profil comme complété (registration_step)
    update_fields.append("registration_step=?")
    update_values.append('profile_created')

    # Exécuter la mise à jour
    update_values.append(session['user'])
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE email=?"
    try:
        c.execute(query, update_values)
        print(f"✅ UPDATE OK: fields={update_fields}", flush=True)
    except Exception as e:
        print(f"❌ ERREUR UPDATE: {e}, query={query}", flush=True)
        import traceback; traceback.print_exc()
        conn.rollback()
        conn.close()
        flash(f"Erreur sauvegarde: {e}", "danger")
        return redirect(url_for('create_profile'))
    
    # Mettre à jour le nom de la maison
    if house_name_input:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        if user_house and user_house[0]:
            c.execute("UPDATE houses SET house_name=?, name=? WHERE id=?", 
                      (house_name_input, house_name_input, user_house[0]))
    
    conn.commit()
    
    # 📛 Propager le changement de nom dans les messages existants
    if name and old_name and name != old_name and profile_house_id:
        try:
            propagate_player_name_change(c, session['user'], old_name, name, profile_house_id)
            conn.commit()
        except Exception as prop_err:
            print(f"⚠️ propagate ignoré: {prop_err}", flush=True)
        _dbg(f"📛 Pseudo mis à jour via profil: '{old_name}' → '{name}' pour {session['user']}")
        
        # 🔌 Notifier via WebSocket
        if SOCKETIO_AVAILABLE and socketio:
            try:
                socketio.emit('player_name_updated', {
                    'email': session['user'],
                    'old_name': old_name,
                    'new_name': name
                }, namespace='/', room=f'house_{profile_house_id}')
            except Exception as ws_err:
                _dbg(f"⚠️ Erreur WebSocket changement nom: {ws_err}")
    conn.close()
    
    flash("Profil mis à jour avec succès ! ✨", "success")
    return redirect(url_for('menu'))


# Routes pour la création de profil
@app.route('/create_profile')
def create_profile():
    _dbg(f"🎭 CREATE_PROFILE GET: user={session.get('user')}, house_name={session.get('house_name')}")
    
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('signup_email'))
    
    # Vérifier si l'utilisateur a déjà un profil (mode modification)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, avatar, avatar_file, house_id, registration_step, avatar_url, avatar_style FROM users WHERE email=?", (session['user'],))
    user = c.fetchone()
    
    change_avatar = False
    current_name = ''
    current_avatar = ''
    current_avatar_file = ''
    current_avatar_url = ''
    current_avatar_style = ''
    current_house_name = ''
    
    if user:
        current_name = user[0] or ''
        current_avatar = user[1] or ''  # Avatar prédéfini (nom de fichier comme homme.png)
        current_avatar_file = user[2] or ''  # Photo uploadée (fichier JPG)
        house_id = user[3]
        registration_step = user[4] or ''
        current_avatar_url = user[5] or ''  # URL DiceBear
        current_avatar_style = user[6] or 'lorelei'  # Style DiceBear
        
        _dbg(f"   📊 User data: name={current_name}, registration_step={registration_step}, house_id={house_id}")
        
        # Mode modification uniquement si le profil est réellement terminé
        # (évite de basculer en édition pendant l'onboarding quand un nom existe déjà)
        if registration_step in ('profile_created', 'complete'):
            change_avatar = True
            _dbg(f"   ⚠️ Profil déjà présent (name={current_name}, step={registration_step}) -> mode modification")
        else:
            _dbg(f"   ✅ Première création de profil")
        
        # Récupérer le nom de la maison si existe
        if house_id:
            c.execute("SELECT house_name FROM houses WHERE id=?", (house_id,))
            house = c.fetchone()
            if house and house[0]:
                current_house_name = house[0]
    
    conn.close()
    
    _dbg(f"   🎨 Affichage create_profile.html (change_avatar={change_avatar})")
    
    return render_template('create_profile.html', 
                           change_avatar=change_avatar,
                           current_name=current_name,
                           current_avatar=current_avatar,
                           current_avatar_file=current_avatar_file,
                           current_avatar_url=current_avatar_url,
                           current_avatar_style=current_avatar_style,
                           current_house_name=current_house_name)

@app.route('/create_profile', methods=['POST'])
def create_profile_post():
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('signup_email'))
    
    name = request.form.get('name', '').strip().capitalize()
    bio = request.form.get('bio', '').strip()
    avatar = request.form.get('avatar', '').strip()
    avatar_style = request.form.get('avatar_style', 'lorelei').strip()
    photo_data = request.form.get('photo_data')
    house_name_input = request.form.get('house_name', '').strip()
    
    import sys
    _dbg(f"🔍 CREATE PROFILE: name={name}, avatar={avatar}, style={avatar_style}")
    sys.stdout.flush()
    
    if not name:
        flash("Le nom est requis", "danger")
        return render_template('create_profile.html')
    
    # Gérer la photo uploadée — stockage data URI en DB (compatible Render)
    photo_data_uri = None
    if photo_data and photo_data.startswith('data:image'):
        photo_data_uri = save_photo_from_base64(photo_data)
        if not photo_data_uri:
            flash("Erreur lors de la sauvegarde de la photo", "warning")
    
    # Mettre à jour le profil utilisateur
    conn = get_db_connection()
    c = conn.cursor()
    
    # Préparer les valeurs de mise à jour
    update_fields = ["name=?"]
    update_values = [name]
    
    if bio:
        update_fields.append("bio=?")
        update_values.append(bio)
    
    # GESTION AVATAR : 3 cas possibles
    if photo_data_uri:
        # CAS 1: Photo uploadée → stockée en DB comme data URI dans avatar_url
        update_fields.extend(["avatar_url=?", "avatar_file=?", "avatar=?", "avatar_style=?"])
        update_values.extend([photo_data_uri, '', '', ''])
        _dbg(f"✅ Avatar = Photo stockée en DB (data URI, {len(photo_data_uri)} chars)")
        
    elif avatar:
        # Détecter le type d'avatar
        is_file = avatar.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        is_emoji = len(avatar) <= 4 and any(ord(c) > 127 for c in avatar)
        is_dicebear = not is_file and not is_emoji
        
        if is_file:
            # CAS 2: Fichier existant (femme.png, homme.png, etc.)
            update_fields.extend(["avatar_file=?", "avatar=?", "avatar_url=?", "avatar_style=?"])
            update_values.extend([avatar, '', '', ''])
            _dbg(f"✅ Avatar = Fichier: {avatar}")
            
        elif is_emoji:
            # CAS 3: Emoji
            update_fields.extend(["avatar=?", "avatar_file=?", "avatar_url=?", "avatar_style=?"])
            update_values.extend([avatar, '', '', ''])
            _dbg(f"✅ Avatar = Emoji: {avatar}")
            
        else:  # is_dicebear
            # CAS 4: DiceBear (seed)
            dicebear_url = f"https://api.dicebear.com/7.x/{avatar_style}/svg?seed={avatar}"
            update_fields.extend(["avatar=?", "avatar_url=?", "avatar_style=?", "avatar_file=?"])
            update_values.extend([avatar, dicebear_url, avatar_style, ''])
            _dbg(f"✅ Avatar = DiceBear: seed={avatar}, style={avatar_style}, url={dicebear_url}")
    
    # Finaliser la requête
    update_fields.append("registration_step=?")
    update_values.append('profile_created')
    update_values.append(session['user'])
    
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE email=?"
    c.execute(query, update_values)
    
    # Créer ou vérifier la maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_house = c.fetchone()
    
    if not user_house or not user_house[0]:
        # Récupérer les infos de session pour créer la maison
        house_type = session.get('house_type', 'family')
        house_name = session.get('house_name', 'Notre Foyer')
        
        from datetime import date
        house_code = generate_house_code()
        today = date.today().isoformat()
        c.execute("""
            INSERT INTO houses (name, house_name, house_type, level, health, mood, code, progress, last_reset_date) 
            VALUES (?, ?, ?, 1, 100, 'happy', ?, 0, ?)
        """, (house_name, house_name, house_type, house_code, today))
        house_id = c.lastrowid
        c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, session['user']))
    
    conn.commit()
    conn.close()
    
    # Nettoyer les infos temporaires de session
    session.pop('house_type', None)
    session.pop('house_name', None)
    session['user_name'] = name
    session['registration_step'] = 'complete'
    
    flash("🎉 Profil créé ! Bienvenue dans l'aventure !", "success")
    return redirect(url_for('menu'))


@app.route('/invite/<code>')
def invite_welcome(code):
    """Route d'invitation personnalisée via SMS - affiche une page d'accueil chaleureuse"""
    house_code = code.strip().upper()
    
    # Vérifier que le code existe
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, house_type FROM houses WHERE code = ?', (house_code,))
    house = c.fetchone()
    
    if not house:
        # Code invalide, rediriger vers la page normale
        conn.close()
        flash('Code d\'invitation invalide', 'error')
        return redirect(url_for('join_house'))
    
    house_id, house_name, house_type = house
    
    # Trouver le créateur de la maison (premier inscrit) pour afficher son nom
    c.execute('SELECT name FROM users WHERE house_id = ? ORDER BY id ASC LIMIT 1', (house_id,))
    inviter = c.fetchone()
    inviter_name = inviter[0] if inviter else 'Ton ami'
    
    conn.close()
    
    return render_template('invite_welcome.html',
                         house_code=house_code,
                         house_name=house_name,
                         house_type=house_type,
                         inviter_name=inviter_name)


@app.route('/join_house', methods=['GET', 'POST'])
def join_house():
    # Récupérer le code depuis l'URL (pour pré-remplir)
    code_from_url = request.args.get('code', '').strip().upper()
    
    if request.method == 'POST':
        house_code = request.form.get('house_code', '').strip().upper()
        user_name = request.form.get('user_name', '').strip().capitalize()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        is_login = request.form.get('is_login') == 'true'  # Nouveau champ pour distinguer connexion/inscription
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Vérifier que le code de maison existe
        c.execute("SELECT id, name FROM houses WHERE code=?", (house_code,))
        house_row = c.fetchone()
        
        if not house_row:
            flash("Code de maison invalide. Vérifiez le code et réessayez.", "danger")
            conn.close()
            return render_template('join_house.html', code=code_from_url)
        
        house_id = house_row[0]
        
        # MODE CONNEXION : utilisateur existant qui rejoint une nouvelle maison
        if is_login:
            if not all([house_code, email, password]):
                flash("Email et mot de passe requis pour se connecter.", "danger")
                conn.close()
                return render_template('join_house.html', code=code_from_url)
            
            # Vérifier les identifiants
            c.execute("SELECT email, password, name FROM users WHERE email=?", (email,))
            user = c.fetchone()
            
            if not user or not check_password_hash(user[1], password):
                flash("Email ou mot de passe incorrect.", "danger")
                conn.close()
                return render_template('join_house.html', code=code_from_url)
            
            # Mettre à jour la maison de l'utilisateur
            c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, email))
            conn.commit()
            
            # 🔌 Récupérer tous les joueurs pour WebSocket (y compris les enfants)
            c.execute("""
                SELECT email, name, avatar, avatar_file, avatar_url, avatar_style, points, player_color
                FROM users 
                WHERE house_id = ?
                ORDER BY name
            """, (house_id,))
            
            players_data = []
            for player in c.fetchall():
                player_email, player_name, player_avatar, player_avatar_file, player_avatar_url, player_avatar_style, player_points, player_color = player
                
                display_avatar_url = None
                if player_avatar_url:
                    display_avatar_url = player_avatar_url
                elif validate_avatar_file(player_avatar_file):
                    display_avatar_url = f"/static/avatars/{player_avatar_file}"
                elif player_avatar and player_avatar_style:
                    display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style}/svg?seed={player_avatar}"
                else:
                    display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style or 'adventurer'}/svg?seed={player_name or player_email}"
                
                players_data.append({
                    'email': player_email,
                    'name': player_name,
                    'avatar_url': display_avatar_url,
                    'points': player_points or 0,
                    'color': player_color
                })
            
            conn.close()
            
            # 🔌 Émettre WebSocket
            try:
                socketio.emit('players_list_update', {
                    'players': players_data,
                    'new_player': user[2],
                    'action': 'player_joined'
                }, namespace='/', room=f'house_{house_id}')
                _dbg(f"🔌 WebSocket: Joueur '{user[2]}' a rejoint la maison (room: house_{house_id})")
            except Exception as ws_err:
                _dbg(f"⚠️ Erreur WebSocket join house: {ws_err}")
            
            # Connecter l'utilisateur
            session.permanent = True
            session['user'] = email
            session['name'] = user[2]
            _log_login(email)
            
            flash(f"🎉 Bienvenue {user[2]} ! Vous avez rejoint la maison !", "success")
            return redirect(url_for('menu'))
        
        # MODE INSCRIPTION : nouvel utilisateur
        else:
            if not all([house_code, user_name, email, password]):
                flash("Tous les champs sont requis.", "danger")
                conn.close()
                return render_template('join_house.html', code=code_from_url)
            
            # Vérifier que le mot de passe fait au moins 6 caractères
            if len(password) < 6:
                flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
                conn.close()
                return render_template('join_house.html', code=code_from_url)
            
            try:
                # Vérifier que l'email n'existe pas déjà
                c.execute("SELECT email FROM users WHERE email=?", (email,))
                if c.fetchone():
                    flash("Cet email est déjà utilisé. Connectez-vous ou utilisez un autre email.", "danger")
                    conn.close()
                    return render_template('join_house.html', code=code_from_url)
                
                # Créer le nouvel utilisateur
                hashed_password = generate_password_hash(password)
                c.execute("""
                    INSERT INTO users (email, password, name, house_id, points, avatar, registration_step)
                    VALUES (?, ?, ?, ?, 0, '🧑', 'email_signup')
                """, (email, hashed_password, user_name, house_id))
                
                conn.commit()
                
                # 🔌 Récupérer tous les joueurs pour WebSocket (y compris les enfants)
                c.execute("""
                    SELECT email, name, avatar, avatar_file, avatar_url, avatar_style, points, player_color
                    FROM users 
                    WHERE house_id = ?
                    ORDER BY name
                """, (house_id,))
                
                players_data = []
                for player in c.fetchall():
                    player_email, player_name, player_avatar, player_avatar_file, player_avatar_url, player_avatar_style, player_points, player_color = player
                    
                    display_avatar_url = None
                    if player_avatar_url:
                        display_avatar_url = player_avatar_url
                    elif validate_avatar_file(player_avatar_file):
                        display_avatar_url = f"/static/avatars/{player_avatar_file}"
                    elif player_avatar and player_avatar_style:
                        display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style}/svg?seed={player_avatar}"
                    else:
                        display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style or 'adventurer'}/svg?seed={player_name or player_email}"
                    
                    players_data.append({
                        'email': player_email,
                        'name': player_name,
                        'avatar_url': display_avatar_url,
                        'points': player_points or 0,
                        'color': player_color
                    })
                
                conn.close()
                
                # 🔌 Émettre WebSocket
                try:
                    socketio.emit('players_list_update', {
                        'players': players_data,
                        'new_player': user_name,
                        'action': 'player_registered'
                    }, namespace='/', room=f'house_{house_id}')
                    _dbg(f"🔌 WebSocket: Nouveau joueur '{user_name}' inscrit (room: house_{house_id})")
                except Exception as ws_err:
                    _dbg(f"⚠️ Erreur WebSocket registration: {ws_err}")
                
                # Connecter automatiquement l'utilisateur
                session.permanent = True
                session['user'] = email
                session['name'] = user_name
                
                flash(f"🎉 Bienvenue {user_name} ! Créez maintenant votre profil et choisissez votre avatar !", "success")
                return redirect(url_for('create_profile'))
                
            except Exception as e:
                conn.close()
                _dbg(f"Erreur lors de la création du compte: {e}")
                flash("Une erreur s'est produite. Veuillez réessayer.", "danger")
                return render_template('join_house.html', code=code_from_url)
    
    # GET: afficher le formulaire avec le code pré-rempli
    return render_template('join_house.html', code=code_from_url)


@app.route('/invite_partner', methods=['GET', 'POST'])
def invite_partner():
    # Vérifier si l'utilisateur est connecté
    if 'user' not in session:
        flash("Connecte-toi pour inviter des partenaires !", "warning")
        return redirect(url_for('login'))
    
    house_code = None
    house_id = None
    house_name = None
    house_type = 'family'  # Valeur par défaut
    
    # Récupérer ou créer une maison pour l'utilisateur
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    
    # Si l'utilisateur n'a pas de maison, en créer une automatiquement
    if not row or not row[0]:
        import random
        import string
        # Générer un code unique de 6 caractères
        house_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Créer la nouvelle maison
        c.execute("INSERT INTO houses (code, name, health, last_reset_date) VALUES (?, ?, ?, date('now'))", 
                 (house_code, '', 100))
        house_id = c.lastrowid
        
        # Associer l'utilisateur à cette maison
        c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, session['user']))
        conn.commit()
        
        flash("🏠 Ta maison a été créée ! Partage le code pour inviter des partenaires.", "success")
    elif row and row[0]:
        house_id = row[0]
        c.execute("SELECT code, house_name, name, house_type FROM houses WHERE id=?", (house_id,))
        house_row = c.fetchone()
        if house_row:
            house_code = house_row[0]
            house_name = house_row[1] if house_row[1] else house_row[2]
            house_type = house_row[3] if house_row[3] else 'family'
    conn.close()

    # Déterminer le contexte : inscription ou depuis manage_players
    source = (request.args.get('source', '') or '').strip().lower()
    posted_source = (request.form.get('invite_source', '') or '').strip().lower() if request.method == 'POST' else ''

    if source == 'manage' or posted_source == 'manage':
        session['invite_source'] = 'manage'
    elif source:
        # Si une autre source explicite est passée, on nettoie le flag précédent
        session.pop('invite_source', None)

    from_manage = (source == 'manage' or posted_source == 'manage' or session.get('invite_source') == 'manage')

    # IMPORTANT: cette page doit rester SIMPLE par défaut.
    # Le mode "configuration maison" ne s'active que si explicitement demandé.
    from_registration = (not from_manage) and (source == 'registration' or posted_source == 'registration')

    if request.method == 'POST':
        import json

        # ─── Récupérer le nom et le type de la maison depuis le formulaire ───
        form_house_name = request.form.get('house_name', '').strip()
        if not form_house_name:
            form_house_name = 'Notre Maison'  # Valeur par défaut si vide
        form_house_type = request.form.get('house_type', 'family').strip()
        if form_house_type not in ('family', 'couple', 'coloc'):
            form_house_type = 'family'

        # Mettre à jour la maison avec le nom et le type choisis
        if house_id and form_house_name:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                "UPDATE houses SET house_name=?, name=?, house_type=? WHERE id=?",
                (form_house_name, form_house_name, form_house_type, house_id)
            )
            conn.commit()
            conn.close()
            house_name = form_house_name
            house_type = form_house_type

        partners_data = request.form.get('partners')
        children_data = request.form.get('children')

        sent_count = 0
        children_created = 0

        # Récupérer le nom de l'utilisateur actuel
        user_name = session.get('user', 'Un ami')
        if 'user' in session:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT name FROM users WHERE email=?", (session['user'],))
            name_row = c.fetchone()
            if name_row and name_row[0]:
                user_name = name_row[0]
            conn.close()

        # Traiter les adultes (envoi SMS)
        if partners_data:
            try:
                partners = json.loads(partners_data)
                for partner in partners:
                    try:
                        send_sms_invitation(
                            partner['phone'],
                            user_name,
                            house_code
                        )
                        sent_count += 1
                    except Exception as e:
                        _dbg(f"Erreur lors de l'envoi du SMS à {partner['name']}: {e}")
            except Exception as e:
                _dbg(f"Erreur lors du traitement des partenaires: {e}")

        # Traiter les enfants (création de comptes)
        if children_data and house_id:
            try:
                children = json.loads(children_data)
                conn = get_db_connection()
                c = conn.cursor()
                for child in children:
                    try:
                        child_name = child.get('name', '').strip()
                        child_avatar = child.get('avatar', '👶')
                        if child_name:
                            import time, re
                            child_email = f"child_{child_name.lower().replace(' ', '_')}_{int(time.time())}@dust.local"
                            # Extraire le seed depuis l'URL DiceBear si nécessaire
                            child_avatar_url = child_avatar
                            child_avatar_seed = ''
                            child_avatar_style = 'adventurer'
                            if 'dicebear.com' in child_avatar:
                                seed_match = re.search(r'seed=([^&]+)', child_avatar)
                                style_match = re.search(r'dicebear\.com/[^/]+/([^/]+)/', child_avatar)
                                child_avatar_seed = seed_match.group(1) if seed_match else child_name.capitalize()
                                child_avatar_style = style_match.group(1) if style_match else 'adventurer'
                            else:
                                child_avatar_seed = child_avatar
                            c.execute("""
                                INSERT INTO users (email, name, house_id, points, avatar, avatar_url, avatar_style, registration_step, is_child_account, created_by)
                                VALUES (?, ?, ?, 0, ?, ?, ?, 'profile_created', 1, ?)
                            """, (child_email, child_name.capitalize(), house_id, child_avatar_seed, child_avatar_url, child_avatar_style, session.get('user', '')))
                            children_created += 1
                    except Exception as e:
                        _dbg(f"Erreur création enfant {child.get('name', '')}: {e}")
                conn.commit()
                conn.close()
            except Exception as e:
                _dbg(f"Erreur traitement enfants: {e}")

        # Messages flash
        messages = []
        if sent_count > 0:
            messages.append(f"📱 {sent_count} invitation{'s' if sent_count > 1 else ''} SMS envoyée{'s' if sent_count > 1 else ''}")
        if children_created > 0:
            messages.append(f"👶 {children_created} profil{'s' if children_created > 1 else ''} enfant{'s' if children_created > 1 else ''} créé{'s' if children_created > 1 else ''}")

        if messages:
            flash("🎉 " + " • ".join(messages), "success")
        elif not partners_data and not children_data:
            flash("C'est parti ! Tu pourras inviter des partenaires plus tard.", "info")

        # Redirection : inscription → profil ; manage → menu
        invite_source = session.pop('invite_source', '')
        if invite_source == 'manage':
            return redirect(url_for('menu'))
        elif from_registration or session.get('registration_step') == 'email_signup':
            # Vérifier si le profil est déjà complet en DB
            try:
                conn_chk = get_db_connection()
                c_chk = conn_chk.cursor()
                c_chk.execute("SELECT registration_step, name FROM users WHERE email=?", (session.get('user', ''),))
                row_chk = c_chk.fetchone()
                conn_chk.close()
                if row_chk and row_chk[0] == 'profile_created' and row_chk[1]:
                    # Profil déjà complet → aller directement au menu
                    return redirect(url_for('menu'))
            except Exception:
                pass
            session['registration_step'] = 'house_named'
            return redirect(url_for('create_profile'))
        else:
            return redirect(url_for('menu'))

    # GET : construire l'URL d'invitation
    join_url = f"{request.host_url}invite/{house_code}" if house_code else ""

    return render_template('invite_partner_new.html',
                           house_code=house_code,
                           house_name=house_name,
                           house_type=house_type,
                           join_url=join_url,
                           from_manage=from_manage,
                           from_registration=from_registration)


@app.route('/partager_invitation')
def partager_invitation():
    """Page simple pour partager l'invitation avec QR Code"""
    if 'user' not in session:
        flash("Connecte-toi pour inviter des partenaires !", "warning")
        return redirect(url_for('login'))
    
    # Récupérer le code et le nom de la maison
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    
    house_code = None
    house_name = None
    if row and row[0]:
        c.execute("SELECT code, house_name, name FROM houses WHERE id=?", (row[0],))
        house_row = c.fetchone()
        if house_row:
            house_code = house_row[0]
            house_name = house_row[1] if house_row[1] else house_row[2]
    conn.close()
    
    if not house_code:
        flash("Aucune maison trouvée. Créez d'abord une maison.", "warning")
        return redirect(url_for('menu'))
    
    # Construire l'URL d'invitation
    join_url = f"{request.host_url}invite/{house_code}"
    
    return render_template('invitation_partner.html', 
                         house_code=house_code,
                         house_name=house_name,
                         join_url=join_url)


@app.route('/update_house_type', methods=['POST'])
def update_house_type():
    """Mettre à jour le type de foyer de la maison"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'}), 401
    
    data = request.get_json()
    house_type = data.get('house_type', 'family')
    
    # Valider le type
    if house_type not in ['family', 'couple', 'coloc']:
        house_type = 'family'
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    
    if not row or not row[0]:
        conn.close()
        return jsonify({'success': False, 'message': 'Pas de maison'}), 404
    
    house_id = row[0]
    
    # Mettre à jour le type de foyer
    c.execute("UPDATE houses SET house_type=? WHERE id=?", (house_type, house_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'house_type': house_type})


# ===============================
# ROUTES SUPPLÉMENTAIRES
# ===============================

@app.route('/fullhouse')
def fullhouse():
    if 'user' not in session:
        flash("Connecte-toi pour accéder à cette page", "warning")
        return redirect(url_for('login'))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_id = c.fetchone()[0]
    c.execute("SELECT name, points, avatar, avatar_url FROM users WHERE house_id=?", (house_id,))
    players = [
        {
            'name': row[0],
            'points': row[1],
            'avatar': row[2],
            'avatar_url': row[3]
        } for row in c.fetchall()
    ]
    conn.close()
    return render_template('fullhouse.html', players=players)

@app.route('/menu')
def menu():
    from datetime import datetime
    _dbg(f"🚨🚨🚨 ROUTE /menu APPELÉE à {datetime.now()} 🚨🚨🚨")
    players = []
    current_user_name = session.get('user', '')
    house_name = None
    show_house_name_form = False
    show_intro_message = False
    house_health = None
    daily_report = []
    player1_name = None
    player1_points = 0
    player1_avatar_url = None
    player1_avatar = None
    player1_avatar_file = None
    player2_name = None
    player2_points = 0
    player2_avatar_url = None
    unread_messages_count = 0
    children_unread = {}  # ✅ Nouvelles pastilles enfants
    unread_by_sender = {}  # Deprecated
    unread_sent_to = {}    # Deprecated
    unread_baby_tracking = 0
    unread_task_added = 0
    has_baby_tracking = False
    house_id = None
    show_onboarding = False
    courses_pending_count = 0
    rooms_with_new_missions = {}
    custom_rooms_db = {}

    # 🚀 OPTIMISATION: Une seule connexion DB pour toute la route /menu
    if 'user' in session:
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            # Vérifier si le profil est complet (nom + avatar + registration_step)
            try:
                c.execute("SELECT name, avatar, avatar_file, house_id, registration_step, has_seen_onboarding, is_child_account FROM users WHERE email=?", (session['user'],))
                user_row = c.fetchone()
                if user_row:
                    user_name, user_avatar, user_avatar_file, house_id, registration_step, has_seen_onboarding, is_child_account = user_row
                else:
                    user_row = None
                    is_child_account = 0
            except Exception:
                # Fallback si colonne has_seen_onboarding/is_child_account absente (ancienne DB)
                try:
                    c.execute("SELECT name, avatar, avatar_file, house_id, registration_step, is_child_account FROM users WHERE email=?", (session['user'],))
                    _row = c.fetchone()
                    if _row:
                        user_name, user_avatar, user_avatar_file, house_id, registration_step, is_child_account = _row
                        has_seen_onboarding = 0
                        user_row = _row
                    else:
                        user_row = None
                        is_child_account = 0
                except Exception:
                    c.execute("SELECT name, avatar, avatar_file, house_id, registration_step FROM users WHERE email=?", (session['user'],))
                    _row = c.fetchone()
                    if _row:
                        user_name, user_avatar, user_avatar_file, house_id, registration_step = _row
                        has_seen_onboarding = 0
                        is_child_account = 0
                        user_row = _row
                    else:
                        user_row = None
                        is_child_account = 0
            
            if not user_row:
                conn.close()
                return redirect(url_for('welcome'))
            
            show_onboarding = not bool(has_seen_onboarding)
            print(f"🏠 MENU CHECK: name={user_name}, avatar={user_avatar}, file={user_avatar_file}, step={registration_step}", flush=True)
            
            # Si le parcours d'inscription n'est pas terminé
            if registration_step not in ('profile_created', 'complete'):
                conn.close()
                flash("Complète ton profil pour commencer à jouer ! 🎭", "info")
                return redirect(url_for('create_profile'))
            
            if not user_name:
                conn.close()
                flash("Complète ton profil pour commencer à jouer ! 🎭", "info")
                return redirect(url_for('create_profile'))
            
            # Si l'utilisateur n'a pas de maison, rediriger vers la page d'invitation
            if not house_id:
                conn.close()
                flash("Crée ou rejoins une maison pour commencer à jouer ! 🏠", "info")
                return redirect(url_for('invite_partner'))
            
            # Réinitialisation quotidienne de la santé/progression de la maison
            try:
                today = date.today().isoformat()
                c.execute("SELECT health, last_reset_date FROM houses WHERE id=?", (house_id,))
                hrow = c.fetchone()
                if hrow:
                    current_last_reset = hrow[1]
                    if current_last_reset != today:
                        c.execute("UPDATE houses SET health=?, last_reset_date=? WHERE id=?", (0, today, house_id))
                        conn.commit()
            except Exception:
                try:
                    today = date.today().isoformat()
                    c.execute("SELECT progress, last_reset_date FROM houses WHERE id=?", (house_id,))
                    prow = c.fetchone()
                    if prow:
                        current_last_reset = prow[1]
                        if current_last_reset != today:
                            c.execute("UPDATE houses SET progress=?, last_reset_date=? WHERE id=?", (0, today, house_id))
                            conn.commit()
                except Exception:
                    pass
            
            # ⚡ Vérifier et effectuer la réinitialisation hebdomadaire des statistiques si nécessaire
            check_weekly_reset(house_id, conn)
            
            # 🚀 Réutiliser la connexion pour get_house_players_points (évite d'en ouvrir une 2ème)
            players = get_house_players_points(house_id, existing_conn=conn)
            _dbg(f"🎯🎯🎯 MENU: {len(players)} joueurs chargés pour house_id={house_id}")

            # Ajouter les streaks pour chaque joueur
            try:
                for p in players:
                    p['streak'] = compute_daily_streak(conn, p.get('email'))
            except Exception:
                pass

            # 🚀 daily_points déjà calculés dans get_house_players_points → pas de recalcul

            # Récupérer nom et santé de la maison (dans la MÊME connexion)
            try:
                c.execute("SELECT name, house_name, health FROM houses WHERE id=?", (house_id,))
                house_row = c.fetchone()
            except sqlite3.OperationalError:
                c.execute("SELECT name, house_name FROM houses WHERE id=?", (house_id,))
                r = c.fetchone()
                house_row = (r[0], r[1], None) if r else None
            if house_row:
                name, house_name_db, house_health_db = house_row
                house_health = house_health_db if house_health_db is not None else 100
                if (not name or not name.strip()) and (not house_name_db or not house_name_db.strip()):
                    show_house_name_form = True
                    house_name = None
                else:
                    house_name = house_name_db.strip() if house_name_db and house_name_db.strip() else name.strip() if name and name.strip() else None
                    if request.args.get('welcome') == '1':
                        show_intro_message = True

            # Rapport quotidien des tâches effectuées (par joueurs)
            try:
                c.execute("""
                    SELECT user_email, category, task_name, points, completed_at
                    FROM completed_tasks
                    WHERE house_id=?
                      AND datetime(completed_at) >= datetime(date('now','localtime'))
                      AND datetime(completed_at) < datetime(date('now','localtime','+1 day'))
                    ORDER BY completed_at DESC
                """, (house_id,))
                rows = c.fetchall()
                if not rows:
                    c.execute("""
                        SELECT user_email, category, task_name, points, completed_at
                        FROM completed_tasks
                        WHERE house_id=?
                          AND date(completed_at) = date('now')
                        ORDER BY completed_at DESC
                    """, (house_id,))
                    rows = c.fetchall()
                diag_rows = []
                if not rows:
                    c.execute("""
                        SELECT user_email, category, task_name, points, completed_at
                        FROM completed_tasks
                        WHERE house_id=?
                        ORDER BY completed_at DESC
                        LIMIT 5
                    """, (house_id,))
                    diag_rows = c.fetchall()
                # 🚀 Réutiliser les avatars déjà chargés dans players au lieu de refaire une requête
                email_to_name = {p.get('email'): p.get('name', p.get('email', '').split('@')[0]) for p in players}
                email_to_avatar = {p.get('email'): p.get('avatar_url', url_for('static', filename='images/default.png')) for p in players}
                daily_report = [
                    {
                        'email': r[0],
                        'name': email_to_name.get(r[0], r[0]),
                        'avatar_url': email_to_avatar.get(r[0], url_for('static', filename='images/default.png')),
                        'category': r[1],
                        'task_name': r[2],
                        'points': r[3],
                        'completed_at': r[4]
                    }
                    for r in rows
                ]
                if not daily_report and diag_rows:
                    daily_report = [
                        {
                            'email': r[0],
                            'name': email_to_name.get(r[0], r[0]),
                            'avatar_url': email_to_avatar.get(r[0], url_for('static', filename='images/default.png')),
                            'category': r[1],
                            'task_name': r[2],
                            'points': r[3],
                            'completed_at': r[4]
                        }
                        for r in diag_rows
                    ]
            except Exception:
                daily_report = []

            # 🔔 Messages non lus — MÊME connexion pour toutes les requêtes
            # ✅ LOGIQUE SIMPLIFIÉE:
            # - unread_messages_count = MES messages reçus non lus (pour mon burger menu)
            # - children_unread = {child_email: count} pour afficher pastilles sur avatars enfants (visible par tous)
            unread_messages_count = get_unread_message_count(session['user'], house_id, existing_conn=conn)
            children_unread = get_children_unread_counts(house_id, existing_conn=conn)
            
            # Deprecated - à supprimer progressivement
            unread_by_sender = {}  # Non utilisé dans nouvelle logique
            unread_sent_to = {}    # Non utilisé dans nouvelle logique
            
            # ✅ Messages baby_tracking et task_added : compteur pour badges burger
            unread_baby_tracking = get_unread_count_by_type(session['user'], house_id, 'baby_tracking', existing_conn=conn, include_own=True)
            unread_task_added = get_unread_count_by_type(session['user'], house_id, 'task_added', existing_conn=conn)
            _dbg(f"🔔 DEBUG menu - {session['user']}: unread_messages_count={unread_messages_count}, baby={unread_baby_tracking}, task_added={unread_task_added}, children_unread={children_unread}")

            # 🛒 Articles non cochés dans la liste de courses (badge onglet navigation)
            courses_pending_count = 0
            try:
                c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (house_id,))
                courses_pending_count = c.fetchone()[0] or 0
            except Exception:
                pass

            # 🍼 Vérifier si la maison utilise le tracking bébé
            try:
                c.execute("SELECT COUNT(*) FROM baby_tracking WHERE house_id=?", (house_id,))
                has_baby_tracking = (c.fetchone()[0] or 0) > 0
            except Exception:
                has_baby_tracking = False
            
            # 🏠 Récupérer les pièces personnalisées AVANT de fermer la connexion
            custom_rooms_db = {}
            if house_id:
                try:
                    c.execute("SELECT room_key, custom_name, custom_image, is_hidden FROM custom_rooms WHERE house_id=?", (house_id,))
                    custom_rooms_db = {row[0]: {'name': row[1], 'image': row[2], 'is_hidden': row[3]} for row in c.fetchall()}
                except Exception as e:
                    _dbg(f"⚠️ Erreur récupération custom_rooms: {e}")
                    custom_rooms_db = {}

            # 🟠 Pièces avec missions non validées — AVANT conn.close()
            rooms_with_new_missions = {}
            if house_id:
                try:
                    c.execute("""
                        SELECT ct.category, COUNT(*) as pending_count FROM custom_tasks ct
                        WHERE ct.house_id = ?
                        AND NOT EXISTS (
                            SELECT 1 FROM completed_tasks ctd
                            WHERE ctd.house_id = ct.house_id
                            AND ctd.category = ct.category
                            AND ctd.completed_at >= ct.created_at
                        )
                        GROUP BY ct.category
                    """, (house_id,))
                    rooms_with_new_missions = {row[0]: row[1] for row in c.fetchall()}
                except Exception as _e_nm:
                    _dbg(f"⚠️ rooms_with_new_missions error: {_e_nm}")

        finally:
            conn.close()

    # 🏠 Construire la liste des pièces avec personnalisations
    custom_rooms_data = []
    # Définir les pièces par défaut (correspond exactement aux 12 cartes du menu)
    ALL_DEFAULT_ROOMS = [
        # Chambres (optionnelles – peuvent être masquées et renommées)
        {'key': 'chambre_parentale', 'name': 'Chambre 1',    'image': 'images/chambreparentale marron.webp', 'category': 'chambre_parentale', 'fixed': False},
        {'key': 'chambre1',          'name': 'Chambre 2',    'image': 'images/chambre1.webp',                'category': 'chambre_parentale',  'fixed': False},
        {'key': 'chambre2',          'name': 'Chambre 3',    'image': 'images/chambre2.webp',                'category': 'chambre_parentale',  'fixed': False},
        {'key': 'chambre_garcon',    'name': 'Chambre 4',    'image': 'images/chambre garçon3.webp',        'category': 'chambre_garcon',     'fixed': False},
        {'key': 'chambre_enfant',    'name': 'Chambre 5',    'image': 'images/chambre enfant 4.webp',       'category': 'chambre_enfant',     'fixed': False},
        {'key': 'chambre_bebe',      'name': 'Chambre bébé', 'image': 'images/chambre bébé4 .webp',         'category': 'chambre_bebe',       'fixed': False},
        # Pièces fixes (ne peuvent pas être masquées, mais renommables)
        {'key': 'salon',    'name': 'Salon',        'image': 'images/salonorange.webp',  'category': 'salon',      'fixed': True},
        {'key': 'cuisine',  'name': 'Cuisine',      'image': 'images/cuisinewoop.webp',  'category': 'cuisine',    'fixed': True},
        {'key': 'bureau',   'name': 'Bureau',       'image': 'images/bureau.webp',       'category': 'piece_bonus', 'fixed': True},
        {'key': 'salle_bain','name': 'Salle de bain','image': 'images/sdbwoop.webp',     'category': 'salle_bain', 'fixed': True},
        {'key': 'toilettes','name': 'Toilettes',    'image': 'images/Wc2.webp',          'category': 'wc',         'fixed': True},
        {'key': 'buanderie','name': 'Buanderie',    'image': 'images/buanderie5.webp',   'category': 'buanderie',  'fixed': True},
        {'key': 'garage',   'name': 'Garage',       'image': 'images/Garage2.webp',      'category': 'garage',     'fixed': False},
    ]
    if house_id:
        for room in ALL_DEFAULT_ROOMS:
            room_data = room.copy()
            
            # Appliquer les personnalisations si elles existent
            if room['key'] in custom_rooms_db:
                custom = custom_rooms_db[room['key']]
                if custom['name']:
                    room_data['name'] = custom['name']
                if custom['image']:
                    room_data['image'] = custom['image']
                room_data['is_hidden'] = bool(custom['is_hidden'])
            else:
                room_data['is_hidden'] = False
            
            # Les pièces fixes ne sont jamais masquées
            if room['fixed']:
                room_data['is_hidden'] = False
            
            # N'ajouter que les pièces non masquées
            if not room_data.get('is_hidden'):
                custom_rooms_data.append(room_data)
    else:
        # Pas de maison : afficher toutes les pièces par défaut
        for room in ALL_DEFAULT_ROOMS:
            room_data = room.copy()
            room_data['is_hidden'] = False
            custom_rooms_data.append(room_data)

    # Préparer les données header: joueur courant et joueur en attente
    if players:
        current_email = session.get('user')
        current_player = None
        for p in players:
            if p.get('email') == current_email:
                current_player = p
                break
        # Joueur courant = player1
        if current_player:
            player1_name = current_player.get('name')
            player1_points = current_player.get('daily_points', 0)
            player1_avatar_url = current_player.get('avatar_url')
            player1_avatar = current_player.get('avatar')
            player1_avatar_file = current_player.get('avatar_file')
            _dbg(f"🔍 DEBUG Avatar Player1: email={current_email}, avatar={player1_avatar}, avatar_url={player1_avatar_url}, avatar_file={player1_avatar_file}")
        else:
            fallback_player = None
            for p in players:
                if p.get('email') == current_email:
                    fallback_player = p
                    break
            
            if fallback_player:
                player1_name = fallback_player.get('name')
                player1_points = fallback_player.get('daily_points', 0)
                player1_avatar_url = fallback_player.get('avatar_url')
                player1_avatar = fallback_player.get('avatar')
                player1_avatar_file = fallback_player.get('avatar_file')
                _dbg(f"⚠️ DEBUG Fallback avec session email: {current_email}, avatar={player1_avatar}")
            else:
                p0 = players[0]
                player1_name = p0.get('name')
                player1_points = p0.get('daily_points', 0)
                player1_avatar_url = p0.get('avatar_url')
                player1_avatar = p0.get('avatar')
                player1_avatar_file = p0.get('avatar_file')
                _dbg(f"⚠️ DEBUG Fallback ultime avec players[0]: email={p0.get('email')}, avatar={player1_avatar}")
        # Joueur en attente = premier autre joueur de la maison
        others = [p for p in players if p.get('email') != current_email]
        if others:
            p2 = others[0]
            player2_name = p2.get('name')
            player2_points = p2.get('daily_points', 0)
            player2_avatar_url = p2.get('avatar_url')
    
    # 🎨 Créer une map de couleurs cohérente pour tous les joueurs
    if players:
        player_emails = [p.get('email') for p in players if p.get('email')]
        color_map = get_player_colors_map(player_emails)
        
        for player in players:
            email = player.get('email')
            if email and email in color_map:
                player['color'] = color_map[email]['vertical']
                player['color_h'] = color_map[email]['horizontal']
            else:
                player['color'] = 'linear-gradient(180deg, #95A5A6 0%, #7F8C8D 100%)'
                player['color_h'] = 'linear-gradient(90deg, #95A5A6 0%, #7F8C8D 100%)'
            # Garantir weekly_points pour tous les joueurs (widget compétition)
            if 'weekly_points' not in player:
                player['weekly_points'] = 0
            if 'is_current_user' not in player:
                player['is_current_user'] = (player.get('email') == session.get('user'))

    # ⚙️ DEV: forcer l'affichage de l'onboarding via ?preview_onboarding=1
    if request.args.get('preview_onboarding') == '1':
        show_onboarding = True

    resp = make_response(render_template(
        'menu.html',
        players=players,
        current_user_name=current_user_name,
        current_user_daily_points=next((p.get('daily_points',0) for p in players if p.get('email')==current_user_name), 0),
        is_child_account=is_child_account if 'is_child_account' in locals() else 0,  # Statut enfant de l'utilisateur actuel
        menu_page=True,
        house_name=house_name,
        show_house_name_form=show_house_name_form,
        show_intro_message=show_intro_message,
        house_health=house_health,
        daily_report=daily_report,
        player1_name=player1_name,
        player1_points=player1_points,
        player1_avatar_url=player1_avatar_url,
        player1_avatar=player1_avatar,
        player1_avatar_file=player1_avatar_file,
        player2_name=player2_name,
        player2_points=player2_points,
        player2_avatar_url=player2_avatar_url,
        unread_messages_count=unread_messages_count,
        children_unread=children_unread,  # ✅ Nouvelles pastilles enfants simplifiées
        unread_by_sender=unread_by_sender,  # Deprecated - à supprimer
        unread_sent_to=unread_sent_to,      # Deprecated - à supprimer
        unread_baby_tracking=unread_baby_tracking,
        unread_task_added=unread_task_added,
        courses_pending_count=courses_pending_count,
        has_baby_tracking=has_baby_tracking,
        custom_rooms=custom_rooms_data,
        show_onboarding=show_onboarding,
        rooms_with_new_missions=rooms_with_new_missions,
    ))
    # Désactiver le cache pour éviter d'afficher d'anciennes valeurs de daily_points
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


# ════════════════════════════════════════════════════════════
# 👤 PAGE PROFIL — Page complète du profil joueur
# ════════════════════════════════════════════════════════════
@app.route('/profil')
def profil():
    return profil_joueur(session.get('user', ''))

@app.route('/profil/<path:player_email>')
def profil_joueur(player_email):
    if 'user' not in session:
        return redirect(url_for('login'))
    current_user_name = session.get('user', '')
    # Rediriger vers /profil si c'est son propre profil (URL propre)
    if player_email == current_user_name and request.endpoint == 'profil_joueur':
        return redirect(url_for('profil'))
    is_own_profile = (player_email == current_user_name)
    player1_name = None
    player1_avatar = None
    player1_avatar_file = None
    player1_avatar_url = None
    house_name = None
    house_id = None
    viewer_house_id = None
    players = []
    unread_baby_tracking = 0
    has_baby_tracking = False
    daily_report = []
    player1_points = 0
    my_rewards_available = []
    my_rewards_used = []
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Maison du visiteur (pour vérification sécurité)
        try:
            c.execute("SELECT house_id FROM users WHERE email=?", (current_user_name,))
            vr = c.fetchone()
            if vr:
                viewer_house_id = vr[0]
        except Exception:
            pass
        # Données du joueur affiché
        try:
            c.execute("SELECT name, avatar, avatar_file, house_id, avatar_url FROM users WHERE email=?", (player_email,))
            row = c.fetchone()
            if row:
                player1_name, player1_avatar, player1_avatar_file, house_id, player1_avatar_url = row
        except Exception:
            pass
        # Sécurité : le joueur affiché doit être dans la même maison
        if house_id and viewer_house_id and house_id != viewer_house_id:
            conn.close()
            return redirect(url_for('menu'))
        if house_id:
            try:
                c.execute("SELECT name, house_name FROM houses WHERE id=?", (house_id,))
                hr = c.fetchone()
                if hr:
                    house_name = (hr[1] or hr[0] or '').strip() or None
            except Exception:
                pass
            try:
                players = get_house_players_points(house_id, existing_conn=conn)
                for p in players:
                    p['is_current_user'] = (p.get('email') == current_user_name)
            except Exception:
                players = []
            try:
                c.execute("SELECT COUNT(*) FROM baby_tracking WHERE house_id=?", (house_id,))
                has_baby_tracking = (c.fetchone()[0] or 0) > 0
            except Exception:
                pass
            try:
                today = date.today().strftime('%Y-%m-%d')
                c.execute("SELECT email, COUNT(*) FROM tasks WHERE house_id=? AND date=? AND done=1 GROUP BY email", (house_id, today))
                daily_report = [{'email': r[0], 'count': r[1]} for r in c.fetchall()]
            except Exception:
                daily_report = []
            if is_own_profile:
                try:
                    unread_baby_tracking = get_unread_count_by_type(current_user_name, house_id, 'baby_tracking', existing_conn=conn, include_own=True)
                except Exception:
                    pass
        # Récompenses : uniquement si c'est son propre profil
        if is_own_profile:
            try:
                c.execute("""
                    SELECT id, reward_text, won_date
                    FROM mystery_rewards
                    WHERE user_email=? AND used=0
                    ORDER BY id DESC
                """, (player_email,))
                my_rewards_available = [{'id': r[0], 'text': r[1], 'date': r[2]} for r in c.fetchall()]
            except Exception:
                my_rewards_available = []
            try:
                c.execute("""
                    SELECT id, reward_text, won_date, used_date
                    FROM mystery_rewards
                    WHERE user_email=? AND used=1
                    ORDER BY used_date DESC
                """, (player_email,))
                my_rewards_used = [{'id': r[0], 'text': r[1], 'won_date': r[2], 'used_date': r[3]} for r in c.fetchall()]
            except Exception:
                my_rewards_used = []
        conn.close()
    except Exception:
        pass
    cp = next((p for p in players if p.get('email') == player_email), None)
    return render_template(
        'profil.html',
        current_user_name=current_user_name,
        player_email=player_email,
        is_own_profile=is_own_profile,
        player1_name=player1_name,
        player1_avatar=player1_avatar,
        player1_avatar_file=player1_avatar_file,
        player1_avatar_url=player1_avatar_url,
        house_name=house_name,
        players=players,
        cp=cp,
        player1_points=player1_points,
        daily_report=daily_report,
        unread_baby_tracking=unread_baby_tracking,
        my_rewards_available=my_rewards_available,
        my_rewards_used=my_rewards_used,
    )


# ════════════════════════════════════════════════════════════
# � CLASSEMENT — Page plein écran
# ════════════════════════════════════════════════════════════
@app.route('/classement')
def classement():
    if 'user' not in session:
        return redirect(url_for('login'))
    current_user_name = session.get('user', '')
    players = []
    house_name = None
    house_id = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT house_id FROM users WHERE email=?", (current_user_name,))
        row = c.fetchone()
        if row:
            house_id = row[0]
        if house_id:
            try:
                c.execute("SELECT name, house_name FROM houses WHERE id=?", (house_id,))
                hr = c.fetchone()
                if hr:
                    house_name = (hr[1] or hr[0] or '').strip() or None
            except Exception:
                pass
            try:
                players = get_house_players_points(house_id, existing_conn=conn)
                for p in players:
                    p['is_current_user'] = (p.get('email') == current_user_name)
            except Exception:
                players = []
        conn.close()
    except Exception:
        pass
    return render_template(
        'classement.html',
        current_user_name=current_user_name,
        players=players,
        house_name=house_name,
    )


# ════════════════════════════════════════════════════════════
# 🎮 GAMEPLAY — Page de fonctionnalités de jeu (malus/bonus)
# ════════════════════════════════════════════════════════════
@app.route('/gameplay')
def gameplay():
    if 'user' not in session:
        return redirect(url_for('login'))
    current_user_name = session.get('user', '')
    players = []
    house_name = None
    house_id = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT house_id FROM users WHERE email=?", (current_user_name,))
        row = c.fetchone()
        if row:
            house_id = row[0]
        if house_id:
            try:
                c.execute("SELECT name, house_name FROM houses WHERE id=?", (house_id,))
                hr = c.fetchone()
                if hr:
                    house_name = (hr[1] or hr[0] or '').strip() or None
            except Exception:
                pass
            try:
                players = get_house_players_points(house_id, existing_conn=conn)
                for p in players:
                    p['is_current_user'] = (p.get('email') == current_user_name)
                    # DEBUG: Afficher les suspicions
                    if p.get('suspicion_active'):
                        _dbg(f"🔍 GAMEPLAY: {p['name']} suspicion_active={p['suspicion_active']}, count={p.get('suspicion_count', 0)}")
            except Exception as ex:
                _dbg(f"❌ Erreur get_house_players_points: {ex}")
                import traceback
                traceback.print_exc()
                players = []
        conn.close()
    except Exception:
        pass
    return render_template(
        'gameplay.html',
        current_user_name=current_user_name,
        players=players,
        house_name=house_name,
    )


# ════════════════════════════════════════════════════════════
# �🎓 ONBOARDING — Marquer comme vu
# ════════════════════════════════════════════════════════════
@app.route('/api/mark_onboarding_seen', methods=['POST'])
def api_mark_onboarding_seen():
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False}), 401
    try:
        conn = get_db_connection()
        conn.execute("UPDATE users SET has_seen_onboarding=1 WHERE email=?", (session['user'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ════════════════════════════════════════════════════════════
# 💀 API MALUS — Envoyer un malus à un adversaire
# ════════════════════════════════════════════════════════════
@app.route('/api/send_malus', methods=['POST'])
def api_send_malus():
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    target_email = str(data.get('target_email', '')).strip()
    reason = str(data.get('reason', '')).strip()
    points = int(data.get('points', -5))
    sender_email = session['user']

    # Sécurité : les points doivent être négatifs et bornés
    if points > 0:
        points = -abs(points)
    if points < -50:
        points = -50

    if not target_email or target_email == sender_email:
        return jsonify({'success': False, 'error': 'Cible invalide'}), 400

    reason_labels = {
        'lazy':     'Fainéant·e',
        'messy':    'A laissé traîner',
        'dishes':   'Vaisselle non rangée',
        'forgot':   'Tâche oubliée',
        'arrache':  'Fait à l\'arrache',
        'presque':  'Presque… mais non',
        'sabotage': 'Sabotage flagrant',
    }
    reason_label = reason_labels.get(reason, 'Malus')

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id, name FROM users WHERE email=?", (sender_email,))
        sender_row = c.fetchone()
        if not sender_row:
            return jsonify({'success': False, 'error': 'Expéditeur introuvable'}), 400
        house_id = sender_row[0]
        sender_name = sender_row[1] or sender_email.split('@')[0]

        c.execute("SELECT house_id, name FROM users WHERE email=?", (target_email,))
        target_row = c.fetchone()
        if not target_row or target_row[0] != house_id:
            return jsonify({'success': False, 'error': 'Cible introuvable dans cette maison'}), 400
        target_name = target_row[1] or target_email.split('@')[0]

        # Limiter à 3 malus envoyés par expéditeur par jour vers la même cible
        from datetime import date as _date
        today = _date.today().isoformat()
        c.execute("""
            SELECT COUNT(*) FROM completed_tasks
            WHERE user_email=? AND category='malus'
            AND task_name LIKE ? AND DATE(completed_at)=?
        """, (target_email, '%' + sender_name + '%', today))
        count_today = c.fetchone()[0]
        if count_today >= 3:
            return jsonify({'success': False, 'error': f'Tu as déjà envoyé 3 malus à {target_name} aujourd\'hui !'}), 200

        # Insérer le malus comme tâche avec points négatifs
        task_name = f'💀 Malus de {sender_name} : {reason_label}'
        c.execute("""
            INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
            VALUES (?, ?, 'malus', ?, ?, CURRENT_TIMESTAMP)
        """, (target_email, task_name, points, house_id))
        # Badge 💀 sur l'avatar de la cible pendant 1 heure
        from datetime import datetime as _dt_malus, timedelta as _td_malus
        skull_until = (_dt_malus.utcnow() + _td_malus(hours=1)).isoformat()
        c.execute("UPDATE users SET skull_expires_at=? WHERE email=?", (skull_until, target_email))
        conn.commit()

        return jsonify({
            'success': True,
            'message': f'💀 Malus envoyé à {target_name} ! ({points} pts)'
        })
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_send_malus: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/send_bonus', methods=['POST'])
def api_send_bonus():
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    target_email = str(data.get('target_email', '')).strip()
    reason = str(data.get('reason', '')).strip()
    points = int(data.get('points', 5))
    sender_email = session['user']

    if points < 0:
        points = abs(points)
    if points > 50:
        points = 50

    if not target_email or target_email == sender_email:
        return jsonify({'success': False, 'error': 'Cible invalide'}), 400

    reason_labels = {
        'bravo':  'Super travail',
        'help':   'A aidé',
        'extra':  'A fait plus',
        'effort': 'On sent l\'effort',
        'wahouh': 'Wahouh incroyable',
        'nice':   'Bonne ambiance',
        'streak': 'Streak remarquable',
    }
    reason_label = reason_labels.get(reason, 'Bonus')

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id, name FROM users WHERE email=?", (sender_email,))
        sender_row = c.fetchone()
        if not sender_row:
            return jsonify({'success': False, 'error': 'Expéditeur introuvable'}), 400
        house_id = sender_row[0]
        sender_name = sender_row[1] or sender_email.split('@')[0]

        c.execute("SELECT house_id, name FROM users WHERE email=?", (target_email,))
        target_row = c.fetchone()
        if not target_row or target_row[0] != house_id:
            return jsonify({'success': False, 'error': 'Cible introuvable dans cette maison'}), 400
        target_name = target_row[1] or target_email.split('@')[0]

        # Max 1 sanction (toutes catégories) par heure vers la même cible
        c.execute("""
            SELECT COUNT(*) FROM completed_tasks
            WHERE user_email=? AND category IN ('malus','bonus')
            AND task_name LIKE ? AND completed_at >= datetime('now', '-1 hour')
        """, (target_email, f'%{sender_name}%'))
        recent_ct = c.fetchone()[0]
        c.execute("""
            SELECT COUNT(*) FROM suspicions
            WHERE suspecting_player_email=? AND suspected_player_email=?
            AND created_at >= datetime('now', '-1 hour')
        """, (sender_email, target_email))
        recent_susp = c.fetchone()[0]
        if recent_ct + recent_susp >= 1:
            return jsonify({'success': False, 'error': f'Tu as déjà sanctionné {target_name} dans la dernière heure. La prochaine sanction devra attendre !'}), 200

        task_name = f'❤️ Bonus de {sender_name} : {reason_label}'
        c.execute("""
            INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
            VALUES (?, ?, 'bonus', ?, ?, CURRENT_TIMESTAMP)
        """, (target_email, task_name, points, house_id))
        # Badge ❤️ sur l'avatar de la cible pendant 1 heure
        from datetime import datetime as _dt_bonus, timedelta as _td_bonus
        bonus_until = (_dt_bonus.utcnow() + _td_bonus(hours=1)).isoformat()
        c.execute("UPDATE users SET bonus_expires_at=? WHERE email=?", (bonus_until, target_email))
        conn.commit()

        return jsonify({'success': True, 'message': f'❤️ Bonus envoyé à {target_name} ! (+{points} pts)'})
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_send_bonus: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════
# 🎡 API ROUE DE LA CHANCE — Tâches impopulaires bonus
# ════════════════════════════════════════════════════════════
@app.route('/api/spin_wheel', methods=['POST'])
def api_spin_wheel():
    """
    Ajoute une tâche obtenue via la roue de la chance.
    La tâche est ajoutée comme custom_task pour le joueur courant.
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    task_name = str(data.get('task_name', '')).strip()
    points = int(data.get('points', 50))
    user_email = session['user']

    if not task_name:
        return jsonify({'success': False, 'error': 'Nom de tâche manquant'}), 400

    # Sécurité : limiter les points entre 30 et 100
    if points < 30:
        points = 30
    if points > 100:
        points = 100

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id, name FROM users WHERE email=?", (user_email,))
        user_row = c.fetchone()
        if not user_row:
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'}), 400
        house_id = user_row[0]
        user_name = user_row[1] or user_email.split('@')[0]

        # Ajouter la tâche comme custom_task dans la catégorie 'wheel' (pour la tracer)
        c.execute("""
            INSERT INTO custom_tasks (house_id, user_email, category, task_name, points, created_at)
            VALUES (?, ?, 'wheel', ?, ?, CURRENT_TIMESTAMP)
        """, (house_id, user_email, task_name, points))
        conn.commit()

        _dbg(f"🎡 Roue de la chance : {user_name} a obtenu '{task_name}' (+{points} pts)")

        return jsonify({
            'success': True,
            'message': f'🎉 Tâche ajoutée : {task_name} (+{points} pts)'
        })
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_spin_wheel: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/complete_wheel_task', methods=['POST'])
def api_complete_wheel_task():
    """Valide une corvée obtenue via la roue et ajoute les points au joueur."""
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    task_name = str(data.get('task_name', '')).strip()
    points = int(data.get('points', 40))
    user_email = session['user']

    if not task_name:
        return jsonify({'success': False, 'error': 'Tâche manquante'}), 400
    if points < 30:
        points = 30
    if points > 100:
        points = 100

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (user_email,))
        row = c.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'}), 400
        house_id = row[0]

        c.execute("""
            INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
            VALUES (?, ?, 'wheel', ?, ?, CURRENT_TIMESTAMP)
        """, (user_email, task_name, points, house_id))
        conn.commit()

        from datetime import date as _d
        today = _d.today().isoformat()
        c.execute("""
            SELECT COALESCE(SUM(points), 0) FROM completed_tasks
            WHERE user_email=? AND house_id=? AND DATE(completed_at)=?
        """, (user_email, house_id, today))
        new_total = int(c.fetchone()[0] or 0)

        _dbg(f"✅ Roue validée : {user_email} -> '{task_name}' +{points} pts (total jour: {new_total})")
        return jsonify({'success': True, 'new_total': new_total})
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_complete_wheel_task: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════
# 🔍 SYSTÈME DE PREUVES — Vigilance sociale
# ════════════════════════════════════════════════════════════

@app.route('/api/give_malus', methods=['POST'])
def api_give_malus():
    """
    Donne un malus à un joueur : retire des points ET ajoute un skull pendant 24h.
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    target_email = str(data.get('target_email', '')).strip()
    task_name = str(data.get('task_name', '')).strip()
    sender_email = session['user']

    if not target_email or target_email == sender_email:
        return jsonify({'success': False, 'error': 'Cible invalide'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Vérifier que l'expéditeur et la cible sont dans la même maison
        c.execute("SELECT house_id, name FROM users WHERE email=?", (sender_email,))
        sender_row = c.fetchone()
        if not sender_row:
            return jsonify({'success': False, 'error': 'Expéditeur introuvable'}), 400
        house_id = sender_row[0]
        sender_name = sender_row[1] or sender_email.split('@')[0]

        c.execute("SELECT house_id, name, COALESCE(skull_count, 0) FROM users WHERE email=?", (target_email,))
        target_row = c.fetchone()
        if not target_row or target_row[0] != house_id:
            return jsonify({'success': False, 'error': 'Cible introuvable dans cette maison'}), 400
        target_name = target_row[1] or target_email.split('@')[0]
        current_skull_count = target_row[2]

        # Limiter à 3 malus par jour vers la même cible
        from datetime import date as _date
        today = _date.today().isoformat()
        c.execute("""
            SELECT COUNT(*) FROM completed_tasks
            WHERE user_email=? AND category='malus'
            AND task_name LIKE ? AND DATE(completed_at)=?
        """, (target_email, '%' + sender_name + '%', today))
        count_today = c.fetchone()[0]
        if count_today >= 3:
            return jsonify({'success': False, 'error': f'Tu as déjà envoyé 3 malus à {target_name} aujourd\'hui !'}), 200

        # Max 1 sanction (toutes catégories) par heure vers la même cible
        c.execute("""
            SELECT COUNT(*) FROM completed_tasks
            WHERE user_email=? AND category IN ('malus','bonus')
            AND task_name LIKE ? AND completed_at >= datetime('now', '-1 hour')
        """, (target_email, f'%{sender_name}%'))
        recent_ct = c.fetchone()[0]
        c.execute("""
            SELECT COUNT(*) FROM suspicions
            WHERE suspecting_player_email=? AND suspected_player_email=?
            AND created_at >= datetime('now', '-1 hour')
        """, (sender_email, target_email))
        recent_susp = c.fetchone()[0]
        if recent_ct + recent_susp >= 1:
            return jsonify({'success': False, 'error': f'Tu as déjà sanctionné {target_name} dans la dernière heure. La prochaine sanction devra attendre !'}), 200

        # Points du malus (négatif)
        points = -10

        # Insérer le malus comme tâche avec points négatifs
        malus_task_name = f'💀 Malus de {sender_name}' + (f' : {task_name}' if task_name else '')
        c.execute("""
            INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
            VALUES (?, ?, 'malus', ?, ?, CURRENT_TIMESTAMP)
        """, (target_email, malus_task_name, points, house_id))

        # 💀 SKULL : Ajouter un skull pendant 1h
        from datetime import timedelta
        skull_expires = (datetime.utcnow() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute("""
            UPDATE users 
            SET skull_count = COALESCE(skull_count, 0) + 1,
                skull_expires_at = ?
            WHERE email=?
        """, (skull_expires, target_email))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'💀 Malus envoyé à {target_name} ! ({points} pts + skull 1h)'
        })
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_give_malus: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/active_malus', methods=['GET'])
def api_active_malus():
    """
    Renvoie la liste des joueurs qui ont un skull actif
    = ayant reçu un malus dans les 60 dernières minutes.
    Basé sur completed_tasks (robuste, pas besoin de skull_expires_at).
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'malus': []}), 200

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify({'malus': []}), 200

        house_id = row[0]

        # Seuil = il y a 60 minutes
        from datetime import timedelta
        since = (datetime.utcnow() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

        # Joueurs ayant reçu un malus dans la dernière heure
        # Cast explicite pour compatibilité PostgreSQL
        c.execute("""
            SELECT ct.user_email, u.name, ct.task_name
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ?
              AND ct.category = 'malus'
              AND ct.completed_at >= CAST(? AS TIMESTAMP)
            ORDER BY ct.completed_at DESC
        """, (house_id, since))

        rows = c.fetchall()

        # Dédupliquer par email (garder le malus le plus récent)
        seen = {}
        for email, name, task_name in rows:
            if email not in seen:
                seen[email] = {
                    'email': email,
                    'name': name or email.split('@')[0],
                    'task_name': task_name,
                }

        return jsonify({'malus': list(seen.values())})
    except Exception as e:
        _dbg(f"ERREUR api_active_malus: {e}")
        return jsonify({'malus': [], 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/active_bonus', methods=['GET'])
def api_active_bonus():
    """
    Renvoie la liste des joueurs qui ont reçu un bonus dans la dernière heure.
    Miroir de api_active_malus mais pour la catégorie 'bonus'.
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'bonus': []}), 200

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify({'bonus': []}), 200

        house_id = row[0]

        from datetime import timedelta
        since = (datetime.utcnow() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

        c.execute("""
            SELECT ct.user_email, u.name, ct.task_name
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ?
              AND ct.category = 'bonus'
              AND ct.completed_at >= CAST(? AS TIMESTAMP)
            ORDER BY ct.completed_at DESC
        """, (house_id, since))

        rows = c.fetchall()

        seen = {}
        for email, name, task_name in rows:
            if email not in seen:
                seen[email] = {
                    'email': email,
                    'name': name or email.split('@')[0],
                    'task_name': task_name,
                }

        return jsonify({'bonus': list(seen.values())})
    except Exception as e:
        _dbg(f"ERREUR api_active_bonus: {e}")
        return jsonify({'bonus': [], 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/house_suspicions', methods=['GET'])
def api_house_suspicions():
    """
    Renvoie TOUTES les suspicions de la maison (publique, visible par tous).
    Similaire à api_active_malus mais pour les suspicions.
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'suspicions': []}), 200

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify({'suspicions': []}), 200

        house_id = row[0]

        # Toutes les suspicions actives ou récentes de la maison
        c.execute("""
            SELECT s.id, 
                   s.suspecting_player_email, u1.name as suspecting_name,
                   s.suspected_player_email, u2.name as suspected_name,
                   s.task_name, s.task_points, s.status, s.photo_path, 
                   s.created_at, s.resolved_at,
                   u2.is_child_account, u2.created_by
            FROM suspicions s
            INNER JOIN users u1 ON s.suspecting_player_email = u1.email
            INNER JOIN users u2 ON s.suspected_player_email = u2.email
            WHERE s.house_id = ?
            ORDER BY 
                CASE s.status 
                    WHEN 'pending' THEN 1
                    WHEN 'awaiting_validation' THEN 2
                    WHEN 'validated' THEN 3
                    WHEN 'rejected' THEN 4
                END,
                s.created_at DESC
            LIMIT 50
        """, (house_id,))

        rows = c.fetchall()
        suspicions = []
        for row in rows:
            # Vérifier si l'utilisateur actuel peut uploader pour un enfant
            is_child = (row[11] == 1)  # is_child_account
            child_parent = row[12]  # created_by
            can_upload_for_child = (is_child and child_parent == session['user'])
            
            suspicions.append({
                'id': row[0],
                'suspecting_email': row[1],
                'suspecting_name': row[2],
                'suspected_email': row[3],
                'suspected_name': row[4],
                'task_name': row[5],
                'task_points': row[6],
                'status': row[7],
                'photo_path': row[8],
                'created_at': str(row[9]),
                'resolved_at': str(row[10]) if row[10] else None,
                # Indiquer qui est l'utilisateur actuel
                'is_suspecting': (row[1] == session['user']),
                'is_suspected': (row[3] == session['user']),
                'can_upload_for_child': can_upload_for_child  # Le parent peut uploader pour l'enfant
            })

        return jsonify({'success': True, 'suspicions': suspicions})
    except Exception as e:
        _dbg(f"ERREUR api_house_suspicions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/active_suspicions', methods=['GET'])
def api_active_suspicions():
    """
    Renvoie la liste des joueurs qui ont une suspicion active (pending ou awaiting_validation).
    Utilisé pour afficher la loupe 🔍 sur les avatars.
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'suspicions': []}), 200

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify({'suspicions': []}), 200

        house_id = row[0]

        # Suspicions actives (pending = en attente de preuve, awaiting_validation = preuve envoyée)
        c.execute("""
            SELECT s.suspected_player_email, u.name, s.status
            FROM suspicions s
            INNER JOIN users u ON s.suspected_player_email = u.email
            WHERE s.house_id = ?
              AND s.status IN ('pending', 'awaiting_validation')
            ORDER BY s.created_at DESC
        """, (house_id,))

        rows = c.fetchall()

        # Dédupliquer par email (garder la suspicion la plus récente)
        seen = {}
        for email, name, status in rows:
            if email not in seen:
                seen[email] = {
                    'email': email,
                    'name': name or email.split('@')[0],
                    'status': status,
                    'icon': '🔍' if status == 'pending' else '📸'
                }

        return jsonify({'suspicions': list(seen.values())})
    except Exception as e:
        _dbg(f"ERREUR api_active_suspicions: {e}")
        return jsonify({'suspicions': [], 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/proof/tasks')
def api_proof_tasks():
    """Tâches récentes des colocataires (dernières 24h) qu'on peut contester."""
    from flask import jsonify
    if 'user' not in session:
        return jsonify([])
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify([])
        house_id = row[0]
        # Tâches des AUTRES joueurs (7 derniers jours), hors malus et preuves
        c.execute("""
            SELECT ct.id, ct.user_email, ct.task_name, ct.points, ct.completed_at,
                   u.name,
                   (SELECT COUNT(*) FROM proof_requests pr
                    WHERE pr.completed_task_id = ct.id
                    AND pr.requester_email = ?) as already_requested
            FROM completed_tasks ct
            JOIN users u ON u.email = ct.user_email
            WHERE ct.house_id=? AND ct.user_email != ?
            AND ct.category NOT IN ('malus','proof_penalty','proof_bonus')
            AND ct.completed_at >= DATETIME('now', '-7 days')
            ORDER BY ct.completed_at DESC
            LIMIT 50
        """, (session['user'], house_id, session['user']))
        rows = c.fetchall()
        tasks = []
        for r in rows:
            tasks.append({
                'id': r[0], 'email': r[1], 'task': r[2],
                'points': r[3], 'at': str(r[4]), 'name': r[5],
                'already_requested': bool(r[6])
            })
        return jsonify(tasks)
    except Exception as e:
        _dbg(f"ERREUR api_proof_tasks: {e}")
        return jsonify([])
    finally:
        conn.close()



@app.route('/api/proof/all')
def api_proof_all():
    """Vue unifiée : toutes les tâches du jour avec statut contestation pour TOUS les joueurs."""
    from flask import jsonify
    if 'user' not in session:
        return jsonify([])
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify([])
        house_id = row[0]
        me = session['user']
        # Toutes les tâches des 24 dernières heures de la maison
        c.execute("""
            SELECT ct.id, ct.user_email, ct.task_name, ct.points, ct.completed_at,
                   u.name,
                   pr.id, pr.status, pr.requester_email, pr.photo_data,
                   (SELECT name FROM users WHERE email = pr.requester_email)
            FROM completed_tasks ct
            JOIN users u ON u.email = ct.user_email
            LEFT JOIN proof_requests pr
                ON pr.completed_task_id = ct.id
                AND pr.status NOT IN ('validated','refuted')
            WHERE ct.house_id = ?
            AND ct.category NOT IN ('malus','proof_penalty','proof_bonus')
            AND ct.completed_at >= DATETIME('now', '-1 day')
            ORDER BY ct.completed_at DESC
            LIMIT 60
        """, (house_id,))
        tasks = []
        for r in c.fetchall():
            task_email = r[1]
            proof_id = r[6]
            proof_status = r[7]
            requester_email = r[8]
            photo_data = r[9]
            req_name = r[10]
            is_mine = (task_email == me)
            am_requester = (requester_email == me)
            am_target = (task_email == me and proof_id is not None)
            can_contest = (not is_mine and proof_id is None)
            tasks.append({
                'id': r[0], 'email': task_email, 'task': r[2],
                'points': r[3], 'at': str(r[4]), 'name': r[5],
                'is_mine': is_mine, 'can_contest': can_contest,
                'proof_id': proof_id, 'proof_status': proof_status,
                'photo_data': photo_data,
                'am_requester': am_requester, 'am_target': am_target,
                'requester_name': req_name or ''
            })
        return jsonify(tasks)
    except Exception as e:
        _dbg(f"ERREUR api_proof_all: {e}")
        return jsonify([])
    finally:
        conn.close()

@app.route('/api/proof/request', methods=['POST'])
def api_proof_request():
    """Demander une preuve photo : coûte 3 pts au demandeur."""
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    data = request.get_json() or {}
    completed_task_id = int(data.get('task_id', 0))
    target_email = str(data.get('target_email', '')).strip()
    task_name = str(data.get('task_name', '')).strip()
    task_points = int(data.get('task_points', 0))
    requester_email = session['user']
    if not target_email or not task_name or not completed_task_id:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400
    if target_email == requester_email:
        return jsonify({'success': False, 'error': 'Tu ne peux pas te demander une preuve à toi-même'}), 400
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id, name FROM users WHERE email=?", (requester_email,))
        req_row = c.fetchone()
        if not req_row:
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'}), 400
        house_id, req_name = req_row[0], req_row[1] or requester_email.split('@')[0]
        # Vérifier que la cible est dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (target_email,))
        tgt_row = c.fetchone()
        if not tgt_row or tgt_row[0] != house_id:
            return jsonify({'success': False, 'error': 'Cible introuvable'}), 400
        # Vérifier pas déjà demandé
        c.execute("SELECT id FROM proof_requests WHERE completed_task_id=? AND requester_email=?",
                  (completed_task_id, requester_email))
        if c.fetchone():
            return jsonify({'success': False, 'error': 'Tu as déjà contesté cette tâche'}), 400
        # Récupérer le nom de la cible pour le message
        c.execute("SELECT name FROM users WHERE email=?", (target_email,))
        tgt_name_row = c.fetchone()
        target_name_display = tgt_name_row[0] if tgt_name_row and tgt_name_row[0] else target_email.split('@')[0]
        # Créer la demande (sans déduction immédiate — points débités à la validation)
        c.execute("""
            INSERT INTO proof_requests (house_id, requester_email, target_email, task_name, task_points, completed_task_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (house_id, requester_email, target_email, task_name, task_points, completed_task_id))
        conn.commit()
        return jsonify({'success': True, 'message': f'🕵️ Contestation lancée ! {target_name_display} doit maintenant envoyer une preuve photo.'})
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_proof_request: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/proof/submit', methods=['POST'])
def api_proof_submit():
    """Soumettre une photo comme preuve. Le demandeur pourra ensuite valider ou réfuter."""
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    data = request.get_json() or {}
    proof_id = int(data.get('proof_id', 0))
    photo_data = str(data.get('photo_data', '')).strip()  # base64 data-URL
    if not proof_id or not photo_data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400
    # Limite taille ~2 Mo en base64
    if len(photo_data) > 2_800_000:
        return jsonify({'success': False, 'error': 'Photo trop grande (max 2 Mo)'}), 400
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT id, target_email, status FROM proof_requests WHERE id=? AND target_email=?",
                  (proof_id, session['user']))
        row = c.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Demande introuvable'}), 404
        if row[2] != 'pending':
            return jsonify({'success': False, 'error': 'Cette demande a déjà une preuve'}), 400
        c.execute("UPDATE proof_requests SET status='submitted', photo_data=? WHERE id=?",
                  (photo_data, proof_id))
        conn.commit()
        return jsonify({'success': True, 'message': '📸 Preuve envoyée ! Le jury va statuer.'})
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_proof_submit: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/proof/validate', methods=['POST'])
def api_proof_validate():
    """
    Valider (preuve ok) ou réfuter (tricherie) une preuve soumise.
    verdict = 'validated' : accusateur perd 10 pts, accusé gagne task_points en bonus
    verdict = 'refuted'   : accusateur gagne 10 pts, accusé perd 10 pts + skull 24h
    """
    from flask import jsonify
    from datetime import datetime, timedelta
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    data = request.get_json() or {}
    proof_id = int(data.get('proof_id', 0))
    verdict = str(data.get('verdict', '')).strip()
    if not proof_id or verdict not in ('validated', 'refuted'):
        return jsonify({'success': False, 'error': 'Paramètres invalides'}), 400
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("""SELECT id, house_id, requester_email, target_email, task_name, task_points, status
                     FROM proof_requests WHERE id=? AND requester_email=?""",
                  (proof_id, session['user']))
        row = c.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Demande introuvable'}), 404
        _, house_id, requester_email, target_email, task_name, task_points, status = row
        if status != 'submitted':
            return jsonify({'success': False, 'error': 'Aucune preuve à valider pour l\'instant'}), 400

        c.execute("SELECT name FROM users WHERE email=?", (target_email,))
        tgt = c.fetchone()
        target_name = tgt[0] if tgt else target_email.split('@')[0]

        if verdict == 'validated':
            # Tâche était vraie → accusateur perd 10 pts
            c.execute("""INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
                         VALUES (?, ?, 'proof_penalty', -10, ?, CURRENT_TIMESTAMP)""",
                      (requester_email, f'🔍 Fausse accusation envers {target_name}', house_id))
            # Accusé gagne bonus équivalent valeur tâche
            bonus = max(task_points, 5)
            c.execute("""INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
                         VALUES (?, ?, 'proof_bonus', ?, ?, CURRENT_TIMESTAMP)""",
                      (target_email, f'✅ Preuve validée : {task_name}', bonus, house_id))
            c.execute("UPDATE proof_requests SET status='validated' WHERE id=?", (proof_id,))
            conn.commit()
            return jsonify({'success': True, 'message': f'✅ Preuve validée ! {target_name} gagne {bonus} pts bonus. Tu perds 10 pts pour fausse accusation.'})
        else:
            # Tricherie confirmée → accusateur gagne 10 pts, accusé perd 10 pts + skull 24h
            c.execute("""INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
                         VALUES (?, ?, 'proof_bonus', 10, ?, CURRENT_TIMESTAMP)""",
                      (requester_email, f'🕵️ Tricherie prouvée : {target_name}', house_id))
            c.execute("""INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
                         VALUES (?, ?, 'proof_penalty', -10, ?, CURRENT_TIMESTAMP)""",
                      (target_email, f'💀 Tricherie prouvée sur : {task_name}', house_id))
            skull_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
            c.execute("""UPDATE users SET skull_count = COALESCE(skull_count, 0) + 1,
                                          skull_expires_at = ?
                         WHERE email=?""", (skull_expires, target_email))
            c.execute("UPDATE proof_requests SET status='refuted' WHERE id=?", (proof_id,))
            conn.commit()
            return jsonify({'success': True, 'message': f'💀 Tricherie prouvée ! {target_name} perd 10 pts et hérite d\'une 💀 24h. Tu gagnes 10 pts !'})
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_proof_validate: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/proof/pending')
def api_proof_pending():
    """Preuves soumises en attente de jugement (pour le demandeur) + demandes envoyées à moi."""
    from flask import jsonify
    if 'user' not in session:
        return jsonify([])
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify([])
        house_id = row[0]
        # Cas 1 : je suis le demandeur ET la preuve a été soumise (à juger)
        c.execute("""
            SELECT pr.id, pr.target_email, pr.task_name, pr.task_points,
                   pr.status, pr.photo_data, u.name, pr.created_at
            FROM proof_requests pr
            JOIN users u ON u.email = pr.target_email
            WHERE pr.house_id=? AND pr.requester_email=? AND pr.status IN ('pending','submitted')
            ORDER BY pr.created_at DESC
        """, (house_id, session['user']))
        sent = [{'id': r[0], 'target_email': r[1], 'task': r[2], 'points': r[3],
                 'status': r[4], 'photo': r[5], 'target_name': r[6], 'created_at': str(r[7]),
                 'role': 'requester'} for r in c.fetchall()]
        # Cas 2 : je suis la cible ET une preuve est demandée (à soumettre)
        c.execute("""
            SELECT pr.id, pr.requester_email, pr.task_name, pr.task_points,
                   pr.status, u.name, pr.created_at
            FROM proof_requests pr
            JOIN users u ON u.email = pr.requester_email
            WHERE pr.house_id=? AND pr.target_email=? AND pr.status='pending'
            ORDER BY pr.created_at DESC
        """, (house_id, session['user']))
        received = [{'id': r[0], 'requester_email': r[1], 'task': r[2], 'points': r[3],
                     'status': r[4], 'requester_name': r[5], 'created_at': str(r[6]),
                     'role': 'target'} for r in c.fetchall()]
        return jsonify({'sent': sent, 'received': received})
    except Exception as e:
        _dbg(f"ERREUR api_proof_pending: {e}")
        return jsonify({'sent': [], 'received': []})
    finally:
        conn.close()


# Simple route de test pour vérifier la connectivité (retourne OK en texte brut)
@app.route('/ping')
def ping():
    return 'OK', 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/api/avatar_proxy')
def avatar_proxy():
    """
    🚀 Proxy local pour les avatars DiceBear - cache en fichier local.
    Évite les appels directs au CDN externe api.dicebear.com depuis le navigateur.
    Usage: /api/avatar_proxy?style=adventurer&seed=xxx
    """
    import urllib.request as _urlreq
    import re as _re
    style = request.args.get('style', 'adventurer')
    seed = request.args.get('seed', 'default')
    # Sanitiser les entrées
    if not _re.match(r'^[a-zA-Z0-9_-]+$', style):
        style = 'adventurer'
    seed = _re.sub(r'[<>"\'\\]', '', str(seed))[:60]
    
    # Dossier de cache
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'avatars_cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = _re.sub(r'[^a-zA-Z0-9_-]', '_', f"{style}_{seed}")
    cache_file = os.path.join(cache_dir, f"{cache_key}.svg")
    
    # Servir depuis le cache si dispo
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            svg_data = f.read()
        resp = make_response(svg_data)
        resp.headers['Content-Type'] = 'image/svg+xml'
        resp.headers['Cache-Control'] = 'public, max-age=604800'  # 7 jours
        return resp
    
    # Sinon: fetcher depuis DiceBear et mettre en cache
    dicebear_url = f'https://api.dicebear.com/7.x/{style}/svg?seed={seed}'
    try:
        req = _urlreq.Request(dicebear_url, headers={'User-Agent': 'CleanBeat/1.0'})
        with _urlreq.urlopen(req, timeout=5) as r:
            svg_data = r.read()
        with open(cache_file, 'wb') as f:
            f.write(svg_data)
        resp = make_response(svg_data)
        resp.headers['Content-Type'] = 'image/svg+xml'
        resp.headers['Cache-Control'] = 'public, max-age=604800'
        return resp
    except Exception:
        # Fallback: rediriger vers DiceBear direct
        from flask import redirect as _redirect
        return _redirect(dicebear_url)

# ════════════════════════════════════════════════════════════
# 🕵️ SYSTÈME DE SUSPICION — Gameplay avec preuves photo
# ════════════════════════════════════════════════════════════

@app.route('/api/emit_suspicion', methods=['POST'])
def api_emit_suspicion():
    """
    Émettre une suspicion sur une tâche complétée par un autre joueur.
    Coût potentiel : 10 points si la suspicion est infondée
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    suspected_email = str(data.get('suspected_email', '')).strip()
    task_name = str(data.get('task_name', '')).strip()
    _tp = data.get('task_points', 0)
    task_points = int(_tp) if _tp not in (None, '', 'null') else 0
    _ctid = data.get('completed_task_id')
    completed_task_id = int(_ctid) if _ctid not in (None, '', 'null') else None
    suspecting_email = session['user']

    if not suspected_email or suspected_email == suspecting_email:
        return jsonify({'success': False, 'error': 'Cible invalide'}), 400

    if not task_name:
        return jsonify({'success': False, 'error': 'Tâche non spécifiée'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Vérifier que les deux joueurs sont dans la même maison
        c.execute("SELECT house_id, name FROM users WHERE email=?", (suspecting_email,))
        suspecting_row = c.fetchone()
        if not suspecting_row:
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'}), 400
        house_id = suspecting_row[0]
        suspecting_name = suspecting_row[1] or suspecting_email.split('@')[0]

        c.execute("SELECT house_id, name FROM users WHERE email=?", (suspected_email,))
        suspected_row = c.fetchone()
        if not suspected_row or suspected_row[0] != house_id:
            return jsonify({'success': False, 'error': 'Joueur introuvable dans cette maison'}), 400
        suspected_name = suspected_row[1] or suspected_email.split('@')[0]

        # Vérifier qu'il n'y a pas déjà une suspicion en attente pour cette tâche
        c.execute("""
            SELECT id FROM suspicions
            WHERE suspected_player_email=? AND task_name=? AND status='pending'
        """, (suspected_email, task_name))
        existing_suspicion = c.fetchone()
        if existing_suspicion:
            return jsonify({'success': False, 'error': 'Une suspicion est déjà en attente pour cette tâche'}), 400

        # Max 1 sanction (toutes catégories) par heure vers le même joueur
        c.execute("""
            SELECT COUNT(*) FROM completed_tasks
            WHERE user_email=? AND category IN ('malus','bonus')
            AND task_name LIKE ? AND completed_at >= datetime('now', '-1 hour')
        """, (suspected_email, f'%{suspecting_name}%'))
        recent_ct = c.fetchone()[0]
        c.execute("""
            SELECT COUNT(*) FROM suspicions
            WHERE suspecting_player_email=? AND suspected_player_email=?
            AND created_at >= datetime('now', '-1 hour')
        """, (suspecting_email, suspected_email))
        recent_susp = c.fetchone()[0]
        if recent_ct + recent_susp >= 1:
            return jsonify({'success': False, 'error': f'Tu as déjà sanctionné {suspected_name} dans la dernière heure. La prochaine sanction devra attendre !'}), 200

        # Créer la suspicion
        c.execute("""
            INSERT INTO suspicions (
                house_id, suspecting_player_email, suspected_player_email,
                task_name, task_points, completed_task_id, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        """, (house_id, suspecting_email, suspected_email, task_name, task_points, completed_task_id))
        
        suspicion_id = c.lastrowid
        conn.commit()

        # TODO: Créer une notification pour le joueur soupçonné
        
        return jsonify({
            'success': True,
            'suspicion_id': suspicion_id,
            'message': f'🔍 Suspicion émise sur {suspected_name}. En attente de preuve...'
        })
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_emit_suspicion: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/upload_proof', methods=['POST'])
def api_upload_proof():
    """
    Le joueur soupçonné upload une photo de preuve
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    suspicion_id = request.form.get('suspicion_id')
    if not suspicion_id:
        return jsonify({'success': False, 'error': 'suspicion_id manquant'}), 400

    # Vérifier qu'un fichier a été envoyé
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'Aucune photo fournie'}), 400

    photo_file = request.files['photo']
    if photo_file.filename == '':
        return jsonify({'success': False, 'error': 'Fichier vide'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Vérifier que la suspicion existe et concerne le bon joueur (ou son parent si c'est un enfant)
        c.execute("""
            SELECT s.suspected_player_email, s.status, u.is_child_account, u.created_by
            FROM suspicions s
            INNER JOIN users u ON s.suspected_player_email = u.email
            WHERE s.id=?
        """, (suspicion_id,))
        suspicion = c.fetchone()
        
        if not suspicion:
            return jsonify({'success': False, 'error': 'Suspicion introuvable'}), 404
        
        suspected_email = suspicion[0]
        is_child = (suspicion[2] == 1)
        child_parent = suspicion[3]
        
        # Autoriser si je suis le soupçonné OU si je suis le parent de l'enfant soupçonné
        is_authorized = (suspected_email == session['user']) or (is_child and child_parent == session['user'])
        
        if not is_authorized:
            return jsonify({'success': False, 'error': 'Cette suspicion ne vous concerne pas'}), 403
        
        if suspicion[1] != 'pending':
            return jsonify({'success': False, 'error': 'Cette suspicion a déjà été traitée'}), 400

        # Sauvegarder la photo
        filename = secure_filename(photo_file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"proof_{suspicion_id}_{timestamp}_{filename}"
        
        # Créer le dossier uploads/proofs s'il n'existe pas
        proofs_dir = os.path.join(app.root_path, 'uploads', 'proofs')
        os.makedirs(proofs_dir, exist_ok=True)
        
        photo_path = os.path.join(proofs_dir, unique_filename)
        photo_file.save(photo_path)
        
        # Enregistrer le chemin relatif dans la BD
        relative_path = f'uploads/proofs/{unique_filename}'
        
        c.execute("""
            UPDATE suspicions
            SET photo_path=?, status='awaiting_validation'
            WHERE id=?
        """, (relative_path, suspicion_id))
        conn.commit()

        return jsonify({
            'success': True,
            'message': '📸 Preuve envoyée ! En attente de validation...',
            'photo_path': relative_path
        })
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_upload_proof: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/validate_proof', methods=['POST'])
def api_validate_proof():
    """
    Le soupçonneux valide ou rejette la preuve photo
    
    Règles :
    - Preuve VALIDÉE (photo convaincante) :
      * Soupçonneux perd 10 points (il avait tort)
      * Soupçonné gagne les points de sa tâche
    
    - Preuve REJETÉE (photo non convaincante) :
      * Soupçonneux ne perd rien (il avait raison)
      * Soupçonné perd 20 points (pénalité pour tricherie)
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    suspicion_id = data.get('suspicion_id')
    is_valid = data.get('is_valid')  # True = valide, False = rejetée

    if suspicion_id is None or is_valid is None:
        return jsonify({'success': False, 'error': 'Paramètres manquants'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Récupérer la suspicion
        c.execute("""
            SELECT suspecting_player_email, suspected_player_email, 
                   task_name, task_points, status, house_id
            FROM suspicions
            WHERE id=?
        """, (suspicion_id,))
        suspicion = c.fetchone()
        
        if not suspicion:
            return jsonify({'success': False, 'error': 'Suspicion introuvable'}), 404
        
        suspecting_email, suspected_email, task_name, task_points, status, house_id = suspicion
        
        if suspecting_email != session['user']:
            return jsonify({'success': False, 'error': 'Seul le soupçonneux peut valider la preuve'}), 403
        
        if status != 'awaiting_validation':
            return jsonify({'success': False, 'error': 'Cette suspicion n\'attend pas de validation'}), 400

        # Récupérer les noms des joueurs
        c.execute("SELECT name FROM users WHERE email=?", (suspecting_email,))
        suspecting_name = (c.fetchone()[0] or suspecting_email.split('@')[0])
        
        c.execute("SELECT name FROM users WHERE email=?", (suspected_email,))
        suspected_name = (c.fetchone()[0] or suspected_email.split('@')[0])

        if is_valid:
            # PREUVE VALIDÉE - La photo est convaincante
            # Le soupçonneux avait tort → perd 10 points
            c.execute("""
                INSERT INTO completed_tasks (
                    user_email, task_name, category, points, house_id, completed_at
                ) VALUES (?, ?, 'suspicion_penalty', -10, ?, CURRENT_TIMESTAMP)
            """, (suspecting_email, f'🔍 Suspicion infondée sur {suspected_name}', house_id))
            
            # Le soupçonné gagne les points de sa tâche
            c.execute("""
                INSERT INTO completed_tasks (
                    user_email, task_name, category, points, house_id, completed_at
                ) VALUES (?, ?, 'suspicion_reward', ?, ?, CURRENT_TIMESTAMP)
            """, (suspected_email, f'✅ Preuve validée : {task_name}', task_points, house_id))
            
            # Marquer la suspicion comme validée
            c.execute("""
                UPDATE suspicions
                SET status='validated', resolved_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (suspicion_id,))
            
            message = f'✅ Preuve acceptée ! {suspected_name} gagne {task_points} pts. Vous perdez 10 pts.'
            
        else:
            # PREUVE REJETÉE - La photo n'est pas convaincante
            # Le soupçonneux avait raison → ne perd rien
            # Le soupçonné perd 20 points (pénalité lourde)
            c.execute("""
                INSERT INTO completed_tasks (
                    user_email, task_name, category, points, house_id, completed_at
                ) VALUES (?, ?, 'suspicion_penalty', -20, ?, CURRENT_TIMESTAMP)
            """, (suspected_email, f'❌ Preuve rejetée : {task_name}', house_id))
            
            # Marquer la suspicion comme rejetée
            c.execute("""
                UPDATE suspicions
                SET status='rejected', resolved_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (suspicion_id,))
            
            message = f'❌ Preuve rejetée ! {suspected_name} perd 20 pts. Vous aviez raison !'

        conn.commit()

        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_validate_proof: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


@app.route('/api/my_suspicions', methods=['GET'])
def api_my_suspicions():
    """
    Récupère les suspicions impliquant l'utilisateur connecté
    (comme soupçonneux ou comme soupçonné)
    """
    from flask import jsonify
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401

    conn = get_db_connection()
    c = conn.cursor()
    try:
        email = session['user']
        
        # Suspicions où je suis le soupçonneux
        c.execute("""
            SELECT s.id, s.suspected_player_email, u.name, s.task_name, 
                   s.task_points, s.status, s.photo_path, s.created_at
            FROM suspicions s
            JOIN users u ON u.email = s.suspected_player_email
            WHERE s.suspecting_player_email=?
            ORDER BY s.created_at DESC
            LIMIT 20
        """, (email,))
        my_suspicions = []
        for row in c.fetchall():
            my_suspicions.append({
                'id': row[0],
                'suspected_email': row[1],
                'suspected_name': row[2],
                'task_name': row[3],
                'task_points': row[4],
                'status': row[5],
                'photo_path': row[6],
                'created_at': str(row[7]),
                'role': 'suspecting'
            })
        
        # Suspicions où je suis soupçonné
        c.execute("""
            SELECT s.id, s.suspecting_player_email, u.name, s.task_name, 
                   s.task_points, s.status, s.photo_path, s.created_at
            FROM suspicions s
            JOIN users u ON u.email = s.suspecting_player_email
            WHERE s.suspected_player_email=?
            ORDER BY s.created_at DESC
            LIMIT 20
        """, (email,))
        against_me = []
        for row in c.fetchall():
            against_me.append({
                'id': row[0],
                'suspecting_email': row[1],
                'suspecting_name': row[2],
                'task_name': row[3],
                'task_points': row[4],
                'status': row[5],
                'photo_path': row[6],
                'created_at': str(row[7]),
                'role': 'suspected'
            })
        
        return jsonify({
            'success': True,
            'my_suspicions': my_suspicions,
            'against_me': against_me
        })
    except Exception as e:
        _dbg(f"ERREUR api_my_suspicions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════
# 🏡 Personnalisation de la maison (pièces)
# ════════════════════════════════════════════════════════════
@app.route('/set_bg_theme', methods=['POST'])
def set_bg_theme():
    if 'user' not in session:
        return {'ok': False, 'error': 'non connecté'}, 401
    theme = request.json.get('theme', 'marron')
    if theme not in BG_THEMES:
        return {'ok': False, 'error': 'thème invalide'}, 400
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET bg_theme=? WHERE email=?", (theme, session['user']))
        conn.commit()
        conn.close()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}, 500


@app.route('/personnaliser_maison', methods=['GET', 'POST'])
def personnaliser_maison():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Récupérer house_id depuis la DB (même pattern que menu())
    house_id = None
    conn_h = get_db_connection()
    ch = conn_h.cursor()
    ch.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row_h = ch.fetchone()
    if row_h:
        house_id = row_h[0]
    conn_h.close()

    if not house_id:
        flash("Crée ou rejoins une maison pour personnaliser les pièces ! 🏠", "info")
        return redirect(url_for('invite_partner'))

    # Liste complète de toutes les pièces (fixe = ne peut pas être masquée)
    ALL_ROOMS = [
        {'key': 'chambre_parentale', 'default_name': 'Chambre 1',     'image': 'images/chambreparentale marron.webp', 'fixed': False},
        {'key': 'chambre1',          'default_name': 'Chambre 2',     'image': 'images/chambre1.webp',                'fixed': False},
        {'key': 'chambre2',          'default_name': 'Chambre 3',     'image': 'images/chambre2.webp',                'fixed': False},
        {'key': 'chambre_garcon',    'default_name': 'Chambre 4',    'image': 'images/chambre garçon3.webp',        'fixed': False},
        {'key': 'chambre_enfant',    'default_name': 'Chambre 5',    'image': 'images/chambre enfant 4.webp',       'fixed': False},
        {'key': 'chambre_bebe',      'default_name': 'Chambre bébé',  'image': 'images/chambre bébé4 .webp',         'fixed': False},
        {'key': 'salon',             'default_name': 'Salon',         'image': 'images/salonorange.webp',             'fixed': True},
        {'key': 'cuisine',           'default_name': 'Cuisine',       'image': 'images/cuisinewoop.webp',             'fixed': True},
        {'key': 'salle_bain',        'default_name': 'Salle de bain', 'image': 'images/sdbwoop.webp',                'fixed': True},
        {'key': 'toilettes',         'default_name': 'Toilettes',     'image': 'images/Wc2.webp',                    'fixed': True},
        {'key': 'buanderie',         'default_name': 'Buanderie',     'image': 'images/buanderie5.webp',              'fixed': True},
        {'key': 'garage',            'default_name': 'Garage',        'image': 'images/Garage2.webp',                'fixed': False},
    ]

    if request.method == 'POST':
        conn = get_db_connection()
        c = conn.cursor()
        try:
            # Mettre à jour le nom de la maison si fourni
            new_house_name = request.form.get('house_name', '').strip()
            if new_house_name:
                c.execute("UPDATE houses SET house_name=? WHERE id=?", (new_house_name, house_id))
            for room in ALL_ROOMS:
                key = room['key']
                custom_name = request.form.get(f'name_{key}', '').strip()
                is_hidden = 0 if room['fixed'] else (1 if request.form.get(f'hidden_{key}') else 0)
                # Stocker None si le nom est vide ou identique au nom par défaut
                if not custom_name or custom_name == room['default_name']:
                    custom_name = None
                c.execute("""
                    INSERT INTO custom_rooms (house_id, room_key, custom_name, is_hidden)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(house_id, room_key) DO UPDATE SET
                        custom_name = excluded.custom_name,
                        is_hidden   = excluded.is_hidden
                """, (house_id, key, custom_name, is_hidden))
            conn.commit()
            # 🔌 WEBSOCKET: Notifier les autres joueurs du changement de pièces/nom maison
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    safe_socketio_emit('house_rooms_updated', {'house_id': house_id},
                                      namespace='/', room=f'house_{house_id}', broadcast=True)
                    _dbg(f"🔌 WebSocket: house_rooms_updated émis pour house_{house_id}")
                except Exception as ws_err:
                    _dbg(f"⚠️ Erreur WebSocket edit_house: {ws_err}")
        except Exception as e:
            conn.rollback()
            _dbg(f"⚠️ edit_house POST error: {e}")
        finally:
            conn.close()
        if request.form.get('house_name', '').strip():
            _invalidate_house_cache(session['user'])  # ⚡ Invalider le cache si nom modifié
        return redirect(url_for('menu'))

    # GET : charger les réglages actuels de la maison
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT room_key, custom_name, is_hidden FROM custom_rooms WHERE house_id=?", (house_id,))
        custom_db = {row[0]: {'name': row[1], 'is_hidden': bool(row[2])} for row in c.fetchall()}
    except Exception:
        custom_db = {}
    finally:
        conn.close()

    rooms_data = []
    for room in ALL_ROOMS:
        r = room.copy()
        cust = custom_db.get(room['key'], {})
        r['current_name'] = cust.get('name') or room['default_name']
        r['is_hidden']    = False if room['fixed'] else cust.get('is_hidden', False)
        rooms_data.append(r)

    # Récupérer les prénoms des membres de la maison pour l'UI
    house_members = []
    try:
        conn_m = get_db_connection()
        cm = conn_m.cursor()
        cm.execute("SELECT name FROM users WHERE house_id=? ORDER BY id", (house_id,))
        house_members = [row[0] for row in cm.fetchall() if row[0]]
        conn_m.close()
    except Exception:
        pass

    # Récupérer le nom actuel de la maison
    current_house_name = ''
    try:
        conn_hn = get_db_connection()
        chn = conn_hn.cursor()
        chn.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
        hn_row = chn.fetchone()
        conn_hn.close()
        if hn_row:
            current_house_name = hn_row[0] or hn_row[1] or ''
    except Exception:
        pass

    return render_template('edit_house.html', rooms=rooms_data, house_members=house_members, current_house_name=current_house_name)



# Page de nettoyage du cache
@app.route('/clear_cache')
def clear_cache_page():
    """Page pour vider le cache du navigateur"""
    return send_from_directory('.', 'clear_cache.html')

# Service Worker — mis en cache les images depuis la racine du domaine
@app.route('/sw.js')
def service_worker():
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/manifest.json')
def manifest():
    response = make_response(send_from_directory('static', 'manifest.json'))
    response.headers['Content-Type'] = 'application/manifest+json'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

# Servir les fichiers uploadés (avatars, preuves, etc.)
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Servir les fichiers du dossier uploads/"""
    import os
    uploads_dir = os.path.join(app.root_path, 'uploads')
    return send_from_directory(uploads_dir, filename)

# Page de nettoyage ULTIME (désinstalle les Service Workers)
@app.route('/force_reload')
def force_reload_page():
    """Page de nettoyage complet avec désinstallation des Service Workers"""
    return render_template('force_reload.html')

# Endpoint de debug pour vérifier les daily_points calculés côté serveur
@app.route('/debug_points')
def debug_points():
    if 'user' not in session:
        return {'error': 'Non connecté', 'redirect': '/login'}, 401
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    if not row or not row[0]:
        conn.close()
        return {'error': 'Aucune maison', 'redirect': '/invite_partner', 'message': 'Crée ou rejoins une maison pour jouer'}, 404
    house_id = row[0]
    players = get_house_players_points(house_id)
    # Calcul des points du jour (heure locale) comme dans /menu
    from datetime import date
    today = date.today().isoformat()
    for p in players:
        email = p.get('email')
        c.execute("SELECT COALESCE(SUM(points),0), COUNT(*) FROM completed_tasks WHERE user_email=? AND DATE(completed_at)=?", (email, today))
        sums = c.fetchone()
        p['daily_points'] = int(sums[0]) if sums and sums[0] is not None else 0
        p['daily_tasks'] = int(sums[1]) if sums and sums[1] is not None else 0
    conn.close()
    # Retour simple en JSON
    return {
        'current_user': session.get('user'),
        'players': players
    }

@app.route('/categorie/<cat>')
def categorie(cat):
    # Normaliser le nom de la catégorie pour correspondre aux clés TASKS_CONFIG
    normalized_cat = normalize_category(cat)
    
    # Récupérer le nom et l'icône de la catégorie
    category_name, category_icon = CATEGORY_NAMES.get(normalized_cat, (cat.replace('_', ' ').title(), '🏠'))
    
    # Préparer la liste des tâches prédéfinies pour la catégorie
    tasks_with_images = []
    tasks_points = []
    if normalized_cat in TASKS_CONFIG:
        tasks_with_images = [(t.get('name'), t.get('image'), t.get('points', 0)) for t in TASKS_CONFIG.get(normalized_cat, [])]
        # Liste parallèle des points pour garantir la correspondance avec task_enhanced (index identique)
        tasks_points = [t.get('points', 0) for t in TASKS_CONFIG.get(normalized_cat, [])]

    # Charger les tâches personnalisées (custom_tasks) pour la maison de l'utilisateur
    custom_tasks = []
    players = []
    overrides = {}
    if 'user' in session:
        conn = get_db_connection()
        c = conn.cursor()
        # Récupérer la maison de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if row and row[0]:
            house_id = row[0]
            # joueurs de la maison
            players = get_house_players_points(house_id)
            # récupérer overrides de points pour cette maison et catégorie
            try:
                c.execute("SELECT task_index, points FROM task_points_overrides WHERE house_id=? AND category=?", (house_id, normalized_cat))
                for idx, pts in c.fetchall():
                    overrides[idx] = int(pts)
            except Exception:
                overrides = {}
            # récupérer tâches personnalisées pour cette maison et catégorie
            try:
                c.execute("SELECT id, task_name, task_image, points, created_by, task_description FROM custom_tasks WHERE house_id=? AND category=?", (house_id, normalized_cat))
                for r in c.fetchall():
                    custom_tasks.append({
                        'id': r[0],
                        'name': r[1],
                        'image': r[2],
                        'points': r[3],
                        'created_by': r[4],
                        'description': r[5] if len(r) > 5 else ''
                    })
            except Exception:
                # si la table n'existe pas ou autre erreur, on ignore
                custom_tasks = []
        # Appliquer les overrides aux points affichés
        if overrides:
            for i in range(len(tasks_points)):
                if i in overrides:
                    tasks_points[i] = overrides[i]
            # Reconstruire tasks_with_images avec les points mis à jour
            tasks_with_images = [(tasks_with_images[i][0], tasks_with_images[i][1], tasks_points[i]) for i in range(len(tasks_with_images))]
        conn.close()

        # 🔔 Marquer comme lus les messages task_added de cette catégorie à la visite
        if house_id:
            try:
                conn3 = get_db_connection()
                c3 = conn3.cursor()
                c3.execute("""
                    SELECT m.id FROM messages m
                    WHERE m.house_id = ? AND m.message_type = 'task_added'
                    AND (m.related_category = ? OR m.related_category IS NULL)
                    AND NOT EXISTS (
                        SELECT 1 FROM message_reads mr
                        WHERE mr.message_id = m.id AND mr.user_email = ?
                    )
                """, (house_id, normalized_cat, session['user']))
                for row3 in c3.fetchall():
                    mark_message_as_read(row3[0], session['user'])
                conn3.close()
            except Exception:
                pass

    # Fil d'activité bébé pour chambre_bebe
    baby_activities = []
    if normalized_cat == 'chambre_bebe' and 'user' in session:
        try:
            conn2 = get_db_connection()
            c2 = conn2.cursor()
            c2.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
            row2 = c2.fetchone()
            if row2 and row2[0]:
                house_id_baby = row2[0]
                
                # 🔔 MARQUER TOUS LES MESSAGES BABY_TRACKING COMME LUS quand on consulte la page
                # Récupérer tous les messages baby_tracking non lus pour cette maison
                c2.execute("""
                    SELECT m.id FROM messages m
                    WHERE m.house_id = ? 
                    AND m.message_type = 'baby_tracking'
                    AND NOT EXISTS (
                        SELECT 1 FROM message_reads mr 
                        WHERE mr.message_id = m.id 
                        AND mr.user_email = ?
                    )
                """, (house_id_baby, session['user']))
                
                unread_baby_msg_ids = [r[0] for r in c2.fetchall()]
                
                # Marquer tous ces messages comme lus
                for msg_id in unread_baby_msg_ids:
                    mark_message_as_read(msg_id, session['user'])
                
                _dbg(f"✅ Chambre bébé visitée par {session['user']}: {len(unread_baby_msg_ids)} messages baby_tracking marqués comme lus")
                
                # 🔌 Émettre un événement WebSocket pour mettre à jour le badge bébé pour l'utilisateur
                if len(unread_baby_msg_ids) > 0:
                    safe_socketio_emit('baby_badge_update', {
                        'user_email': session['user'],
                        'baby_unread_count': 0  # Badge à 0 car on a tout marqué comme lu
                    }, namespace='/', room=f'house_{house_id_baby}', broadcast=True)
                    _dbg(f"✅ WebSocket baby_badge_update émis pour {session['user']} - badge à 0")
                
                # Récupérer les activités pour affichage
                c2.execute("""
                    SELECT m.content, m.timestamp, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style
                    FROM messages m
                    LEFT JOIN users u ON m.sender_email = u.email
                    WHERE m.house_id = ? AND m.message_type = 'baby_tracking'
                    ORDER BY m.id DESC LIMIT 30
                """, (house_id_baby,))
                for row in c2.fetchall():
                    content, ts, uname, avatar, avatar_file, avatar_url, avatar_style = row
                    # Formater la date en français : "samedi 21 mars"
                    date_fr = ''
                    if ts is not None:
                        try:
                            from datetime import datetime as _dt2
                            _JOURS_FR = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
                            _MOIS_FR = ['','janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
                            if isinstance(ts, str):
                                _d = _dt2.fromisoformat(ts.replace('T', ' ')[:19])
                            else:
                                _d = ts
                            date_fr = f"{_JOURS_FR[_d.weekday()]} {_d.day} {_MOIS_FR[_d.month]}"
                        except Exception:
                            date_fr = str(ts)[:10]
                    # Préparer l'avatar
                    display_avatar = '👤'
                    if avatar_file and avatar_file.strip():
                        display_avatar = f"/static/avatars/{avatar_file}"
                    elif avatar_url:
                        if 'dicebear.com/8.x' in avatar_url:
                            avatar_url = avatar_url.replace('dicebear.com/8.x', 'dicebear.com/7.x')
                        display_avatar = avatar_url
                    elif avatar and len(str(avatar)) <= 4:
                        display_avatar = avatar
                    elif avatar:
                        style = avatar_style if avatar_style else 'adventurer'
                        display_avatar = f"https://api.dicebear.com/7.x/{style}/svg?seed={avatar}&backgroundColor=transparent"
                    baby_activities.append({
                        'content': content,
                        'date_fr': date_fr,
                        'name': uname or 'Inconnu',
                        'avatar': display_avatar,
                    })
        except Exception as _e:
            _dbg(f"⚠️ baby_activities error: {_e}")
            baby_activities = []
        finally:
            try:
                conn2.close()
            except Exception:
                pass

    return render_template('tasks.html', category=cat, category_name=category_name, category_icon=category_icon, tasks_with_images=tasks_with_images, tasks_points=tasks_points, custom_tasks=custom_tasks, players=players, hide_header=True, baby_activities=baby_activities)


# --- Routes minimales pour éviter les erreurs de BuildError dans tasks.html ---

# Dictionnaire des noms et icônes de catégories
CATEGORY_NAMES = {
    'salon': ('Salon', '🛋️'),
    'cuisine': ('Cuisine', '🍳'),
    'buanderie': ('Buanderie', '👕'),
    'toilettes': ('Toilettes', '🚽'),
    'chambre': ('Chambre', '🛏️'),
    'chambre_parentale': ('Chambre', '🛏️'),
    'salle_bain': ('Salle de bain', '🛁'),
    'chambre_enfant': ('Chambre Enfant', '🧸'),
    'chambre_garcon': ('Chambre Enfant', '🧸'),
    'chambre_bebe': ('Chambre Bébé', '👶'),
    'chambre_ado': ('Zone Ados', '🎮'),
    'piece_bonus': ('Bureau', '🖥️'),
    'garage': ('Garage', '🚗'),
}

# Route pour ajouter ou modifier une tâche personnalisée (GET: formulaire, POST: traitement)
@app.route('/add_task/<cat>', methods=['GET', 'POST'])
@app.route('/edit_custom_task/<cat>/<int:task_id>', methods=['GET', 'POST'])
def add_task_page(cat, task_id=None):
    if 'user' not in session:
        flash("Connecte-toi pour créer une mission.", "warning")
        return redirect(url_for('login'))

    # Normaliser le nom de la catégorie
    normalized_cat = normalize_category(cat)

    # Nom et icône de la catégorie
    category_name, category_icon = CATEGORY_NAMES.get(normalized_cat, (cat.replace('_', ' ').title(), '🏠'))

    # Récupérer la maison de l'utilisateur
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    if not row or not row[0]:
        conn.close()
        flash("Maison introuvable.", "danger")
        return redirect(url_for('menu'))
    house_id = row[0]

    # Si édition, charger la tâche existante
    existing_task = None
    if task_id:
        c.execute("SELECT id, task_name, task_description, task_image, points, created_by FROM custom_tasks WHERE id=? AND house_id=?", (task_id, house_id))
        task_row = c.fetchone()
        if task_row:
            existing_task = {
                'id': task_row[0],
                'name': task_row[1],
                'description': task_row[2] or '',
                'image': task_row[3],
                'points': task_row[4] or 10,
                'created_by': task_row[5]
            }
            # Vérifier que l'utilisateur est le créateur
            if existing_task['created_by'] != session['user']:
                conn.close()
                flash("Tu ne peux modifier que tes propres missions.", "danger")
                return redirect(url_for('categorie', cat=cat))
        else:
            conn.close()
            flash("Mission introuvable.", "danger")
            return redirect(url_for('categorie', cat=cat))

    if request.method == 'POST':
        task_name = request.form.get('task_name', '').strip()
        task_description = request.form.get('task_description', '').strip()
        points = request.form.get('points', 10)
        try:
            points = int(points)
        except Exception:
            points = 10
        
        # Gestion de l'image - priorité au fichier uploadé, sinon image sélectionnée
        task_image_filename = None
        
        # Vérifier si un fichier a été uploadé
        if 'task_image' in request.files:
            file = request.files['task_image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[1].lower()
                filename = f"custom_{uuid.uuid4().hex}.{ext}"
                image_path = os.path.join('static', 'images', filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                file.save(image_path)
                task_image_filename = filename
        
        # Si pas de fichier uploadé, utiliser l'image sélectionnée
        if not task_image_filename:
            task_image_filename = request.form.get('task_image_select', '').strip() or None
        
        # Si toujours pas d'image et en mode édition, garder l'ancienne
        if not task_image_filename and existing_task:
            task_image_filename = existing_task.get('image')

        if task_id and existing_task:
            # Mode édition - UPDATE
            c.execute("""
                UPDATE custom_tasks 
                SET task_name=?, task_description=?, task_image=?, points=?
                WHERE id=? AND house_id=?
            """, (task_name, task_description, task_image_filename, points, task_id, house_id))
            conn.commit()
            conn.close()
        else:
            # Mode création - INSERT
            c.execute("""
                INSERT INTO custom_tasks (house_id, task_name, task_description, category, task_image, points, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (house_id, task_name, task_description, normalized_cat, task_image_filename, points, session['user']))
            conn.commit()
            
            # 🎯 Créer un message automatique pour notifier l'ajout de tâche
            try:
                # Récupérer le nom du créateur
                c.execute("SELECT name FROM users WHERE email=?", (session['user'],))
                creator_row = c.fetchone()
                creator_name = creator_row[0] if creator_row and creator_row[0] else session['user'].split('@')[0]
                
                message_content = f"🆕 {creator_name} a ajouté une nouvelle tâche : '{task_name}' dans {category_name} ({points} pts)"
                create_system_message(house_id, message_content, 'task_added', sender_email=session['user'], related_category=normalized_cat)
            except Exception as _e_msg:
                print(f'⚠️ Erreur création message task_added: {_e_msg}', flush=True)

            # 🔌 WebSocket : notifier tous les joueurs de la maison en temps réel
            try:
                safe_socketio_emit('task_added_notification', {
                    'category': normalized_cat,
                    'task_name': task_name,
                    'creator': session['user']
                }, namespace='/', room=f'house_{house_id}', broadcast=True)
            except Exception as _ws_err:
                _dbg(f'⚠️ Erreur WebSocket task_added: {_ws_err}')

            conn.close()
        
        return redirect(url_for('categorie', cat=cat))

    conn.close()
    # Afficher le formulaire
    return render_template('add_custom_task.html', 
                           category=cat, 
                           category_name=category_name,
                           category_icon=category_icon,
                           task=existing_task,
                           hide_header=True)

# Mettre à jour les points d'une tâche prédéfinie (override par maison)
@app.route('/update_task_points/<cat>/<int:task_id>', methods=['POST'])
def update_task_points(cat, task_id):
    if 'user' not in session:
        flash("Connecte-toi pour modifier les points.", "warning")
        return redirect(url_for('login'))
    
    # Normaliser le nom de la catégorie
    normalized_cat = normalize_category(cat)
    
    points_raw = request.form.get('points', '').strip()
    try:
        new_points = int(points_raw)
    except Exception:
        new_points = 0
    if new_points < 0:
        new_points = 0
    if new_points > 999:
        new_points = 999

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    house_id = row[0] if row else None
    if not house_id:
        conn.close()
        flash("Crée ou rejoins une maison pour personnaliser les tâches ! 🏠", "info")
        return redirect(url_for('invite_partner'))

    try:
        c.execute(
            """
            INSERT INTO task_points_overrides (house_id, category, task_index, points)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(house_id, category, task_index)
            DO UPDATE SET points=excluded.points
            """,
            (house_id, normalized_cat, task_id, new_points)
        )
        conn.commit()
        flash("Points mis à jour ✔", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Erreur mise à jour des points: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for('categorie', cat=cat))

# Mettre à jour les points d'une tâche personnalisée
@app.route('/update_custom_task_points/<cat>/<int:task_id>', methods=['POST'])
def update_custom_task_points(cat, task_id):
    if 'user' not in session:
        flash("Connecte-toi pour modifier les points.", "warning")
        return redirect(url_for('login'))
    points_raw = request.form.get('points', '').strip()
    try:
        new_points = int(points_raw)
    except Exception:
        new_points = 0
    if new_points < 0:
        new_points = 0
    if new_points > 999:
        new_points = 999

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    house_id = row[0] if row else None
    if not house_id:
        conn.close()
        flash("Crée ou rejoins une maison pour personnaliser les tâches ! 🏠", "info")
        return redirect(url_for('invite_partner'))
    try:
        # Ne mettre à jour que si la tâche appartient à la même maison
        c.execute("UPDATE custom_tasks SET points=? WHERE id=? AND house_id=?", (new_points, task_id, house_id))
        conn.commit()
        flash("Points de la mission personnalisée mis à jour ✔", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Erreur mise à jour: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('categorie', cat=cat))

@app.route('/task_page/<cat>/<int:task_id>')
def task_page(cat, task_id):
    # Affiche une page simple ou un message temporaire
    return f"Page de la tâche {task_id} pour la catégorie : {cat} (à implémenter)"

@app.route('/custom_task_page/<int:task_id>', methods=['GET', 'POST'])
def custom_task_page(task_id):
    """
    Page de validation pour les tâches personnalisées (créées par les utilisateurs)
    Similaire à task_enhanced mais pour les custom_tasks
    """
    if 'user' not in session:
        flash("Connecte-toi pour accéder à cette tâche.", "warning")
        return redirect(url_for('signup_email'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la tâche personnalisée (colonnes: task_name, task_description, task_image)
    c.execute("SELECT id, task_name, task_description, points, category, task_image, created_by, house_id FROM custom_tasks WHERE id=?", (task_id,))
    row = c.fetchone()
    
    if not row:
        flash("Tâche personnalisée introuvable.", "warning")
        conn.close()
        return redirect(url_for('menu'))
    
    task_name = row[1] or "Tâche personnalisée"
    task_description = row[2] or ""
    task_points = row[3] if row[3] is not None else 0
    category = row[4] or "autre"
    task_image = row[5] or "default.png"
    created_by = row[6]
    task_house_id = row[7]
    
    # Vérifier que l'utilisateur a accès à cette tâche (même maison)
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    user_house_id = user_row[0] if user_row else None
    
    if task_house_id and user_house_id != task_house_id:
        flash("Tu n'as pas accès à cette tâche.", "warning")
        conn.close()
        return redirect(url_for('menu'))
    
    # Récupérer les joueurs et stats
    players = []
    total_points = 0
    daily_points = 0
    daily_tasks = 0
    
    total_points = get_user_points(session['user'])
    if user_house_id:
        players = get_house_players_points(user_house_id)
        # calculs journaliers
        from datetime import date
        today = date.today().isoformat()
        c.execute("SELECT SUM(points), COUNT(*) FROM completed_tasks WHERE user_email=? AND DATE(completed_at)=?", (session['user'], today))
        sums = c.fetchone()
        if sums and sums[0] is not None:
            try:
                daily_points = int(sums[0])
            except Exception:
                daily_points = 0
        if sums and sums[1] is not None:
            try:
                daily_tasks = int(sums[1])
            except Exception:
                daily_tasks = 0
    
    if request.method == 'POST':
        # Valider la tâche personnalisée
        from datetime import datetime, date
        import random
        today = date.today().isoformat()
        
        # 🍼 Tâches bébé : aucune restriction (biberon, couche, dormir bébé...)
        baby_unlimited_tasks = [
            'biberon', 'couche', 'couches', 'dormir', 'donner le biberon', 'changer les couches'
        ]
        is_baby_unlimited = any(kw.lower() in task_name.lower() for kw in baby_unlimited_tasks)
        
        # 🍳 Tâches cuisine : max 2 fois par jour
        is_kitchen_task = 'cuisine' in (category or '').lower()
        
        if is_baby_unlimited:
            pass  # Aucune restriction pour les tâches bébé
        elif is_kitchen_task:
            c.execute("SELECT COUNT(*) FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at)=?", (session['user'], category, task_name, today))
            if c.fetchone()[0] >= 2:
                funny_messages = [
                    f"🍳 '{task_name}' c'est la 3ème fois ! Max 2 fois par jour en cuisine 😅",
                    f"⚡ Wow ! '{task_name}' déjà 2 fois aujourd'hui ! Repose-toi ! 💪",
                    f"🏆 '{task_name}' × 2 c'est déjà super ! On s'arrête là 😊",
                ]
                flash(random.choice(funny_messages), "warning")
                conn.close()
                return redirect(url_for('menu'))
        else:
            c.execute("SELECT id FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at)=?", (session['user'], category, task_name, today))
            if c.fetchone():
                # 🎭 Messages humoristiques avec le vrai nom de la tâche
                funny_messages = [
                    f"✅ Tu as déjà validé '{task_name}' aujourd'hui ! Une fois suffit 😊",
                    f"🎯 '{task_name}' c'est fait ! Passe à autre chose champion(ne) ! 💪",
                    f"⚡ '{task_name}' déjà validé ! Tu es tellement efficace que tu oublies ce que tu as fait 😄",
                    f"🏆 '{task_name}' : CHECK ! Pas besoin de le refaire, promis !",
                    f"😎 Relax ! '{task_name}' est déjà dans ta liste de victoires du jour !",
                    f"🔄 '{task_name}' ? Encore ? Tu l'as déjà fait aujourd'hui ! 😅",
                    f"🌟 Woah ! '{task_name}' a déjà été validé. Tu veux un trophée ? 🏅",
                    f"🎪 C'est pas Groundhog Day ! '{task_name}' est déjà coché ✓",
                ]
                flash(random.choice(funny_messages), "warning")
                conn.close()
                return redirect(url_for('menu'))
        
        # Récupérer le joueur qui a fait la tâche (depuis le formulaire)
        _raw_pe = request.form.get('player_email', '')
        player_email = _raw_pe if _raw_pe else session['user']
        
        # Vérifier que ce joueur est bien dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (player_email,))
        player_row = c.fetchone()
        if not player_row or player_row[0] != user_house_id:
            flash("Erreur : joueur invalide", "danger")
            conn.close()
            return redirect(url_for('menu'))
        
        # Insérer la tâche complétée
        try:
            c.execute("INSERT INTO completed_tasks (user_email, house_id, category, task_name, points, completed_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                     (player_email, user_house_id, category, task_name, task_points))
            c.execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE email=?", (task_points, player_email))
            
            # Augmenter la santé de la maison
            try:
                c.execute("SELECT health FROM houses WHERE id=?", (user_house_id,))
                hrow = c.fetchone()
                current_health = hrow[0] if hrow and hrow[0] is not None else 0
                new_health = min(current_health + 1, 100)
                c.execute("UPDATE houses SET health=? WHERE id=?", (new_health, user_house_id))
            except Exception:
                try:
                    c.execute("SELECT progress FROM houses WHERE id=?", (user_house_id,))
                    prow = c.fetchone()
                    current_progress = prow[0] if prow and prow[0] is not None else 0
                    new_progress = min(current_progress + 1, 100)
                    c.execute("UPDATE houses SET progress=? WHERE id=?", (new_progress, user_house_id))
                except Exception:
                    pass
            
            # Récupérer le nom du joueur pour l'affichage
            try:
                c.execute("SELECT name FROM users WHERE email=?", (player_email,))
                nrow = c.fetchone()
                player_name = (nrow[0] if nrow and nrow[0] else player_email.split('@')[0])
            except Exception:
                player_name = player_email.split('@')[0]

            conn.commit()

            # Marquer les task_added de cette catégorie comme lus pour l'utilisateur qui valide
            try:
                conn_tr = get_db_connection()
                c_tr = conn_tr.cursor()
                c_tr.execute("""
                    SELECT m.id FROM messages m
                    WHERE m.house_id = ? AND m.message_type = 'task_added'
                    AND (m.related_category = ? OR m.related_category IS NULL)
                    AND NOT EXISTS (
                        SELECT 1 FROM message_reads mr
                        WHERE mr.message_id = m.id AND mr.user_email = ?
                    )
                """, (user_house_id, category, session['user']))
                for _r in c_tr.fetchall():
                    mark_message_as_read(_r[0], session['user'])
                conn_tr.close()
            except Exception:
                pass

            # � WEBSOCKET: Notifier APRÈS commit pour garantir cohérence des données
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    conn_ws = get_db_connection()
                    c_ws = conn_ws.cursor()
                    c_ws.execute("""
                        SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
                               COALESCE(SUM(ct.points), 0) as daily_points
                        FROM users u
                        LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                            AND DATE(ct.completed_at) = DATE('now')
                        WHERE u.house_id = ?
                        GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style, u.points
                        ORDER BY daily_points DESC, u.points DESC
                    """, (user_house_id,))
                    players_data_ws = [{'email': p[0], 'name': p[1], 'avatar': p[2], 'avatar_url': p[3],
                                        'avatar_file': p[4], 'total_points': p[5] or 0,
                                        'daily_points': int(p[6]) if p[6] else 0} for p in c_ws.fetchall()]
                    conn_ws.close()
                    safe_socketio_emit('players_points_update', {
                        'players': players_data_ws, 'updated_player': player_email
                    }, namespace='/', room=f'house_{user_house_id}', broadcast=True)
                    _dbg(f"🔌 WebSocket: Diffusion mise à jour points pour {player_email}")
                except Exception as ws_err:
                    _dbg(f"⚠️ Erreur WebSocket points: {ws_err}")

            # �👶 Sauvegarder les données de suivi bébé si présentes
            tracking_time = request.form.get('tracking_time')
            bottle_ml = request.form.get('bottle_ml')
            observations = request.form.get('observations')
            
            _dbg(f"🔍 CUSTOM TASK BABY TRACKING - Task: {task_name}, Player: {player_name}, Time: {tracking_time}, ML: {bottle_ml}")
            
            if tracking_time:  # Si données de suivi présentes
                _dbg(f"✅ Tracking time présent: {tracking_time}")
                try:
                    # Déterminer le type de tâche bébé
                    task_type = None
                    if 'biberon' in task_name.lower():
                        task_type = 'biberon'
                    elif 'couche' in task_name.lower():
                        task_type = 'couches'
                    elif 'dormir' in task_name.lower():
                        task_type = 'sommeil'
                    
                    _dbg(f"🔍 Type de tâche détecté: {task_type}")
                    
                    if task_type:
                        _dbg(f"✅ Insertion dans baby_tracking: user={player_email}, house={user_house_id}, type={task_type}")
                        # Sauvegarder dans baby_tracking
                        c.execute("""
                            INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (player_email, user_house_id, task_type, tracking_time, bottle_ml if bottle_ml else None, observations))
                        conn.commit()
                        _dbg(f"✅ Enregistré dans baby_tracking")
                        
                        # Créer un message détaillé pour le partenaire
                        if task_type == 'biberon':
                            ml_text = f" ({bottle_ml} ml)" if bottle_ml else ""
                            message_text = f"🍼 {player_name} a donné le biberon à {tracking_time}{ml_text}"
                            if observations:
                                message_text += f"\n📝 {observations}"
                        elif task_type == 'couches':
                            message_text = f"👶 {player_name} a changé les couches à {tracking_time}"
                            if observations:
                                message_text += f"\n📝 {observations}"
                        else:  # sommeil
                            message_text = f"😴 {player_name} a couché bébé à {tracking_time}"
                            if observations:
                                message_text += f"\n📝 {observations}"
                        
                        _dbg(f"📨 Création message: {message_text}")
                        create_system_message(user_house_id, message_text, 'baby_tracking', sender_email=player_email)
                        _dbg(f"✅ Message créé avec succès!")
                except Exception as e:
                    _dbg(f"⚠️ Erreur sauvegarde baby tracking: {e}")
                    import traceback
                    traceback.print_exc()
                    # Ne pas bloquer la validation si le tracking échoue
            else:
                _dbg(f"⚠️ PAS de tracking_time - formulaire non rempli")
            
            # 🎯 Messages automatiques désactivés
            # Les messages ne sont plus envoyés lors de la validation pour éviter l'encombrement
            # try:
            #     message_content = f"✅ {player_name} a validé '{task_name}' (+{task_points} pts)"
            #     create_system_message(user_house_id, message_content, 'task_completed')
            #     
            #     # 💬 Envoyer un message de félicitation si le joueur a fait 3 tâches ou plus aujourd'hui
            #     try:
            #         today = date.today().isoformat()
            #         c_check = conn.cursor()
            #         c_check.execute("""
            #             SELECT COUNT(*) FROM completed_tasks 
            #             WHERE user_email=? AND DATE(completed_at)=?
            #         """, (player_email, today))
            #         task_count = c_check.fetchone()[0]
            #         
            #         if task_count >= 3 and task_count % 3 == 0:  # À chaque multiple de 3
            #             congrats_msg = get_house_personality_message('congratulation', player_name)
            #             create_system_message(user_house_id, congrats_msg, 'congratulation')
            #     except Exception:
            #         pass  # Ne pas bloquer si ça échoue
            #         
            # except Exception:
            #     pass  # Ne pas bloquer si le message échoue
            
            # flash(f"Tâche validée ! +{task_points} pts pour {player_name}", "success")
        except Exception as e:
            flash(f"Erreur lors de la validation : {e}", "danger")
            conn.rollback()
        finally:
            conn.close()
        
        import time
        # Passer le bénéficiaire pour animer le bon avatar dans le menu (email + nom pour fallback)
        return redirect(url_for('menu', ts=int(time.time()), pts=task_points, who=player_email, whon=player_name))
    
    conn.close()
    
    # GET -> afficher la page améliorée (réutiliser le template task_page_enhanced)
    norm_cat_custom = normalize_category(category)
    cat_name_custom, cat_icon_custom = CATEGORY_NAMES.get(norm_cat_custom, (category.replace('_', ' ').title(), '🏠'))
    return render_template('task_page_enhanced.html', 
                          task_name=task_name, 
                          task_image=task_image, 
                          task_points=task_points, 
                          task_description=task_description,
                          fun_text="",  # Pas de fun_text pour les tâches personnalisées
                          ad_text=None,
                          ad_link=None,
                          players=players, 
                          daily_points=daily_points, 
                          daily_tasks=daily_tasks, 
                          total_points=total_points, 
                          category=category,
                          task_id=task_id,
                          current_task_id=task_id,
                          is_custom_task=True,
                          category_name=cat_name_custom,
                          category_icon=cat_icon_custom)


@app.route('/task_enhanced/<cat>/<int:task_id>', methods=['GET', 'POST'])
def task_enhanced(cat, task_id):
    # Normaliser le nom de la catégorie
    normalized_cat = normalize_category(cat)
    
    # Affiche la page 'enhanced' d'une tâche et permet de la valider (POST)
    if normalized_cat not in TASKS_CONFIG or task_id < 0 or task_id >= len(TASKS_CONFIG.get(normalized_cat, [])):
        # Si tâche non définie, afficher message simple
        flash("Tâche introuvable.", "warning")
        return redirect(url_for('categorie', cat=cat))

    task = TASKS_CONFIG[normalized_cat][task_id]
    task_name = task.get('name')
    
    # 🔍 DEBUG: Voir quel task_name est passé au template
    import sys
    _dbg(f"\n🎯🎯🎯 [TASK_ENHANCED GET] 🎯🎯🎯", flush=True)
    _dbg(f"   URL: /task_enhanced/{cat}/{task_id}", flush=True)
    _dbg(f"   normalized_cat: {normalized_cat}", flush=True)
    _dbg(f"   task_id: {task_id}", flush=True)
    _dbg(f"   task_name passé au template: '{task_name}'", flush=True)
    _dbg(f"🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯\n", flush=True)
    sys.stdout.flush()
    
    task_image = task.get('image')
    task_points = task.get('points', 0)
    task_description = task.get('description')
    fun_text = task.get('fun_text', '')
    ad_text = task.get('ad_text')
    ad_link = task.get('ad_link')

    # Récupérer joueurs et stats si utilisateur connecté
    players = []
    total_points = 0
    daily_points = 0
    daily_tasks = 0
    if 'user' in session:
        total_points = get_user_points(session['user'])
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if row and row[0]:
            house_id = row[0]
            players = get_house_players_points(house_id)
            # Override des points si défini pour cette maison/catégorie/tâche
            try:
                c.execute("SELECT points FROM task_points_overrides WHERE house_id=? AND category=? AND task_index=?", (house_id, normalized_cat, task_id))
                orow = c.fetchone()
                if orow and orow[0] is not None:
                    try:
                        task_points = int(orow[0])
                    except Exception:
                        pass
            except Exception:
                pass
            # calculs journaliers
            from datetime import date
            today = date.today().isoformat()
            # Utiliser l'heure locale pour correspondre à l'affichage du menu
            c.execute("SELECT SUM(points), COUNT(*) FROM completed_tasks WHERE user_email=? AND DATE(completed_at)=?", (session['user'], today))
            sums = c.fetchone()
            if sums and sums[0] is not None:
                try:
                    daily_points = int(sums[0])
                except Exception:
                    daily_points = 0
            if sums and sums[1] is not None:
                try:
                    daily_tasks = int(sums[1])
                except Exception:
                    daily_tasks = 0
        conn.close()

    if request.method == 'POST':
        # Valider la tâche pour l'utilisateur courant
        if 'user' not in session:
            flash("Connecte-toi pour valider une tâche.", "warning")
            return redirect(url_for('signup_email'))

        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer le joueur qui a fait la tâche (depuis le formulaire)
        _raw_player_email = request.form.get('player_email', '')
        player_email = _raw_player_email if _raw_player_email else session['user']
        
        # LOGS DE DEBUG
        _dbg(f"🎯 [VALIDATION] Utilisateur connecté: {session['user']}")
        _dbg(f"🎯 [VALIDATION] Joueur sélectionné (player_email): {player_email}")
        _dbg(f"🎯 [VALIDATION] Tâche: {task_name} ({task_points} pts)")
        
        # Vérifier que l'utilisateur connecté et le joueur sélectionné sont dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        user_house_id = row[0] if row else None
        
        c.execute("SELECT house_id FROM users WHERE email=?", (player_email,))
        player_row = c.fetchone()
        player_house_id = player_row[0] if player_row else None
        
        # Si les maisons ne correspondent pas, refuser
        if not user_house_id or not player_house_id or user_house_id != player_house_id:
            flash("Erreur : joueur invalide", "danger")
            conn.close()
            return redirect(url_for('menu'))
        
        house_id = user_house_id

        # Re-récupérer les points avec overrides pour être sûr d'avoir la bonne valeur
        final_task_points = task.get('points', 0)
        if house_id:
            try:
                c.execute("SELECT points FROM task_points_overrides WHERE house_id=? AND category=? AND task_index=?", (house_id, normalized_cat, task_id))
                orow = c.fetchone()
                if orow and orow[0] is not None:
                    final_task_points = int(orow[0])
            except Exception:
                pass

        from datetime import datetime, date
        import random
        today = date.today().isoformat()
        
        # 🍼 Tâches bébé : aucune restriction (biberon, couche, dormir bébé...)
        baby_unlimited_tasks = [
            'biberon', 'couche', 'couches', 'dormir', 'donner le biberon', 'changer les couches'
        ]
        is_baby_unlimited = any(kw.lower() in task_name.lower() for kw in baby_unlimited_tasks)
        
        # 🍳 Tâches cuisine : max 2 fois par jour
        is_kitchen_task = 'cuisine' in (normalized_cat or '').lower()
        
        if is_baby_unlimited:
            pass  # Aucune restriction pour les tâches bébé
        elif is_kitchen_task:
            c.execute("SELECT COUNT(*) FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at)=?", (player_email, normalized_cat, task_name, today))
            if c.fetchone()[0] >= 2:
                funny_messages = [
                    f"🍳 '{task_name}' c'est la 3ème fois ! Max 2 fois par jour en cuisine 😅",
                    f"⚡ Wow ! '{task_name}' déjà 2 fois aujourd'hui ! Repose-toi ! 💪",
                    f"🏆 '{task_name}' × 2 c'est déjà super ! On s'arrête là 😊",
                ]
                funny_message = random.choice(funny_messages)
                flash(funny_message, "warning")
                conn.close()
                return redirect(url_for('menu'))
        else:
            # Vérifier doublon sur la journée locale POUR LE JOUEUR QUI VALIDE
            c.execute("SELECT id FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at)=?", (player_email, normalized_cat, task_name, today))
            if c.fetchone():
                # 🎭 Messages humoristiques avec le vrai nom de la tâche
                funny_messages = [
                    f"✅ Tu as déjà validé '{task_name}' aujourd'hui ! Une fois suffit 😊",
                    f"🎯 '{task_name}' c'est fait ! Passe à autre chose champion(ne) ! 💪",
                    f"⚡ '{task_name}' déjà validé ! Tu es tellement efficace que tu oublies ce que tu as fait 😄",
                    f"🏆 '{task_name}' : CHECK ! Pas besoin de le refaire, promis !",
                    f"😎 Relax ! '{task_name}' est déjà dans ta liste de victoires du jour !",
                    f"🔄 '{task_name}' ? Encore ? Tu l'as déjà fait aujourd'hui ! 😅",
                    f"🌟 Woah ! '{task_name}' a déjà été validé. Tu veux un trophée ? 🏅",
                    f"🎪 C'est pas Groundhog Day ! '{task_name}' est déjà coché ✓",
                ]
                funny_message = random.choice(funny_messages)
                flash(funny_message, "warning")
                conn.close()
                return redirect(url_for('menu'))

        # insérer la tâche complétée POUR LE JOUEUR SÉLECTIONNÉ
        try:
            # Utiliser CURRENT_TIMESTAMP pour completed_at afin de correspondre aux requêtes de calcul
            c.execute("INSERT INTO completed_tasks (user_email, house_id, category, task_name, points, completed_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", (player_email, house_id, normalized_cat, task_name, final_task_points))
            # ajouter les points AU JOUEUR SÉLECTIONNÉ
            c.execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE email=?", (final_task_points, player_email))
            
            # LOGS DE DEBUG
            _dbg(f"✅ [VALIDATION] Points attribués à: {player_email}")
            _dbg(f"✅ [VALIDATION] Montant: {final_task_points} points")
            
            # augmenter la santé/progression de la maison
            try:
                # récupérer santé actuelle
                c.execute("SELECT health FROM houses WHERE id=?", (house_id,))
                row = c.fetchone()
                current_health = row[0] if row and row[0] is not None else 0
                # règle: +1 par tâche validée (cap à 100)
                new_health = current_health + 1
                if new_health > 100:
                    new_health = 100
                c.execute("UPDATE houses SET health=? WHERE id=?", (new_health, house_id))
            except Exception:
                # compatibilité schémas sans 'health': utiliser 'progress'
                try:
                    c.execute("SELECT progress FROM houses WHERE id=?", (house_id,))
                    row = c.fetchone()
                    current_progress = row[0] if row and row[0] is not None else 0
                    new_progress = current_progress + 1
                    if new_progress > 100:
                        new_progress = 100
                    c.execute("UPDATE houses SET progress=? WHERE id=?", (new_progress, house_id))
                except Exception:
                    pass
            # Récupérer le nom du joueur pour l'affichage
            try:
                c.execute("SELECT name FROM users WHERE email=?", (player_email,))
                nrow = c.fetchone()
                player_name = (nrow[0] if nrow and nrow[0] else player_email.split('@')[0])
            except Exception:
                player_name = player_email.split('@')[0]

            conn.commit()

            # Marquer les task_added de cette catégorie comme lus pour l'utilisateur qui valide
            try:
                conn_tr2 = get_db_connection()
                c_tr2 = conn_tr2.cursor()
                c_tr2.execute("""
                    SELECT m.id FROM messages m
                    WHERE m.house_id = ? AND m.message_type = 'task_added'
                    AND (m.related_category = ? OR m.related_category IS NULL)
                    AND NOT EXISTS (
                        SELECT 1 FROM message_reads mr
                        WHERE mr.message_id = m.id AND mr.user_email = ?
                    )
                """, (house_id, normalized_cat, session['user']))
                for _r2 in c_tr2.fetchall():
                    mark_message_as_read(_r2[0], session['user'])
                conn_tr2.close()
            except Exception:
                pass

            # � WEBSOCKET: Notifier APRÈS commit pour garantir cohérence des données
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    conn_ws2 = get_db_connection()
                    c_ws2 = conn_ws2.cursor()
                    c_ws2.execute("""
                        SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
                               COALESCE(SUM(ct.points), 0) as daily_points
                        FROM users u
                        LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                            AND DATE(ct.completed_at) = DATE('now')
                        WHERE u.house_id = ?
                        GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style, u.points
                        ORDER BY daily_points DESC, u.points DESC
                    """, (house_id,))
                    players_data2 = [{'email': p[0], 'name': p[1], 'avatar': p[2], 'avatar_url': p[3],
                                      'avatar_file': p[4], 'total_points': p[5] or 0,
                                      'daily_points': int(p[6]) if p[6] else 0} for p in c_ws2.fetchall()]
                    conn_ws2.close()
                    safe_socketio_emit('players_points_update', {
                        'players': players_data2, 'updated_player': player_email
                    }, namespace='/', room=f'house_{house_id}', broadcast=True)
                    _dbg(f"🔌 WebSocket: Diffusion mise à jour points pour {player_email}")
                except Exception as ws_err:
                    _dbg(f"⚠️ Erreur WebSocket points: {ws_err}")

            # �👶 Sauvegarder les données de suivi bébé si présentes
            tracking_time = request.form.get('tracking_time')
            bottle_ml = request.form.get('bottle_ml')
            observations = request.form.get('observations')
            
            _dbg(f"🔍 BABY TRACKING - Task: {task_name}, Player: {player_name}, Time: {tracking_time}, ML: {bottle_ml}")
            
            if tracking_time:  # Si données de suivi présentes
                _dbg(f"✅ Tracking time présent: {tracking_time}")
                try:
                    # Déterminer le type de tâche bébé
                    task_type = None
                    if 'biberon' in task_name.lower():
                        task_type = 'biberon'
                    elif 'couche' in task_name.lower():
                        task_type = 'couches'
                    elif 'dormir' in task_name.lower():
                        task_type = 'sommeil'
                    
                    _dbg(f"🔍 Type de tâche détecté: {task_type}")
                    
                    if task_type:
                        _dbg(f"✅ Insertion dans baby_tracking: user={player_email}, house={house_id}, type={task_type}")
                        # Sauvegarder dans baby_tracking
                        c.execute("""
                            INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (player_email, house_id, task_type, tracking_time, bottle_ml if bottle_ml else None, observations))
                        conn.commit()
                        _dbg(f"✅ Enregistré dans baby_tracking")
                        
                        # Créer un message détaillé pour le partenaire
                        if task_type == 'biberon':
                            ml_text = f" ({bottle_ml} ml)" if bottle_ml else ""
                            message_text = f"🍼 {player_name} a donné le biberon à {tracking_time}{ml_text}"
                            if observations:
                                message_text += f"\n📝 {observations}"
                        elif task_type == 'couches':
                            message_text = f"👶 {player_name} a changé les couches à {tracking_time}"
                            if observations:
                                message_text += f"\n📝 {observations}"
                        else:  # sommeil
                            message_text = f"😴 {player_name} a couché bébé à {tracking_time}"
                            if observations:
                                message_text += f"\n📝 {observations}"
                        
                        _dbg(f"📨 Création message: {message_text}")
                        create_system_message(house_id, message_text, 'baby_tracking', sender_email=player_email)
                        _dbg(f"✅ Message créé avec succès!")
                except Exception as e:
                    _dbg(f"⚠️ Erreur sauvegarde baby tracking: {e}")
                    import traceback
                    traceback.print_exc()
                    # Ne pas bloquer la validation si le tracking échoue
            else:
                _dbg(f"⏭️ Pas de tracking_time fourni - formulaire baby tracking non rempli")
            
            # 🎯 Messages automatiques désactivés
            # Les messages ne sont plus envoyés lors de la validation pour éviter l'encombrement
            # try:
            #     message_content = f"✅ {player_name} a validé '{task_name}' (+{final_task_points} pts)"
            #     create_system_message(house_id, message_content, 'task_completed')
            #     
            #     # 💬 Envoyer un message de félicitation si le joueur a fait 3 tâches ou plus aujourd'hui
            #     try:
            #         today = date.today().isoformat()
            #         c_check = conn.cursor()
            #         c_check.execute("""
            #             SELECT COUNT(*) FROM completed_tasks 
            #             WHERE user_email=? AND DATE(completed_at)=?
            #         """, (player_email, today))
            #         task_count = c_check.fetchone()[0]
            #         
            #         if task_count >= 3 and task_count % 3 == 0:  # À chaque multiple de 3
            #             congrats_msg = get_house_personality_message('congratulation', player_name)
            #             create_system_message(house_id, congrats_msg, 'congratulation')
            #     except Exception:
            #         pass  # Ne pas bloquer si ça échoue
            #         
            # except Exception:
            #     pass  # Ne pas bloquer si le message échoue
            
            # flash(f"Tâche validée ! +{final_task_points} pts pour {player_name}", "success")
        except Exception as e:
            flash(f"Erreur lors de la validation : {e}", "danger")
            conn.rollback()
        finally:
            conn.close()

        # Après validation, retourner au menu avec paramètres pour animation
        import time
        # Passer le bénéficiaire pour animer le bon avatar dans le menu (email + nom pour fallback)
        return redirect(url_for('menu', ts=int(time.time()), pts=final_task_points, who=player_email, whon=player_name))

    # GET -> afficher la page améliorée
    # 🎨 DEBUG: Afficher les couleurs des joueurs
    _dbg(f"🎨 [TASK_ENHANCED] Joueurs passés au template:")
    for p in players:
        _dbg(f"   • {p.get('name', 'N/A')}: color={p.get('color', 'NONE')}")
    
    # 🔧 DEBUG: Afficher task_id passé au template
    _dbg(f"🔧 [TASK_ENHANCED] task_id passé au template: {task_id}")
    _dbg(f"🔧 [TASK_ENHANCED] task_name: {task_name}")
    _dbg(f"🔧 [TASK_ENHANCED] category: {cat}")
    
    category_name_display, category_icon_display = CATEGORY_NAMES.get(normalized_cat, (cat.replace('_', ' ').title(), '🏠'))
    return render_template('task_page_enhanced.html', task_name=task_name, task_image=task_image, task_points=task_points, task_description=task_description, fun_text=fun_text, ad_text=ad_text, ad_link=ad_link, players=players, daily_points=daily_points, daily_tasks=daily_tasks, total_points=total_points, category=cat, task_id=task_id, current_task_id=task_id, hide_header=True, category_name=category_name_display, category_icon=category_icon_display)


# 🔧 Route de test pour debug task_id
@app.route('/debug_task_id/<cat>/<int:tid>')
def debug_task_id(cat, tid):
    return f"<html><body><h1>DEBUG</h1><p>cat={cat}, tid={tid}</p><script>var taskId = {tid}; console.log('taskId:', taskId);</script></body></html>"


# � API : Valider une tâche en AJAX (pour permettre le son automatique)
@app.route('/api/validate_task', methods=['POST'])
def api_validate_task():
    """
    Valide une tâche via AJAX sans rechargement de page.
    Retourne les infos nécessaires pour jouer le son et afficher l'animation.
    """
    _dbg("="*80)
    _dbg("🎯 API VALIDATE_TASK APPELÉE !")
    _dbg("="*80)
    
    from flask import jsonify
    import time
    from datetime import datetime, date
    import random
    
    if 'user' not in session:
        _dbg("❌ Utilisateur non connecté - session vide ou expirée")
        _dbg(f"📋 Session actuelle: {dict(session) if session else 'Aucune session'}")
        # ✅ Retourner 401 SANS body JSON pour éviter l'affichage du popup
        return '', 401
    
    # Données simplifiées pour performance
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400
    
    task_type = data.get('task_type')  # 'custom' ou 'standard'
    task_id = data.get('task_id')
    task_name_from_payload = data.get('task_name')  # ✅ Nom envoyé par le frontend
    category = data.get('category')
    # ⚠️ FIX: data.get('player_email', default) retourne None si la clé existe avec valeur null
    # → utiliser 'or' pour le fallback vers l'utilisateur connecté
    player_email = data.get('player_email') or session['user']
    
    import sys
    _dbg(f"\n{'='*60}", flush=True)
    _dbg(f"🔍 [DEBUG VALIDATION] Début de la validation", flush=True)
    _dbg(f"{'='*60}", flush=True)
    _dbg(f"📥 Données JSON brutes: {data}", flush=True)
    _dbg(f"📥 Données reçues du payload:", flush=True)
    _dbg(f"   - task_name_from_payload: '{task_name_from_payload}' (type: {type(task_name_from_payload).__name__})", flush=True)
    _dbg(f"   - category: '{category}'", flush=True)
    _dbg(f"   - task_id: {task_id}", flush=True)
    _dbg(f"   - task_type: '{task_type}'", flush=True)
    _dbg(f"   - player_email: '{player_email}'", flush=True)
    _dbg(f"{'='*60}\n", flush=True)
    sys.stdout.flush()
    
    # Pour les tâches avec baby tracking
    tracking_time = data.get('tracking_time')
    bottle_ml = data.get('bottle_ml')
    observations = data.get('observations')
    
    _dbg(f"🍼 [BABY DEBUG] Données reçues:")
    _dbg(f"   - tracking_time: '{tracking_time}' (type: {type(tracking_time)})")
    _dbg(f"   - bottle_ml: '{bottle_ml}' (type: {type(bottle_ml)})")
    _dbg(f"   - observations: '{observations}' (type: {type(observations)})")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Récupérer house_id de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_row = c.fetchone()
        user_house_id = user_row[0] if user_row else None
        
        if not user_house_id:
            return jsonify({'success': False, 'error': 'Maison non trouvée'}), 400
        
        # Vérifier que le joueur est dans la même maison
        c.execute("SELECT house_id, name FROM users WHERE email=?", (player_email,))
        player_row = c.fetchone()
        if not player_row or player_row[0] != user_house_id:
            return jsonify({'success': False, 'error': 'Joueur invalide'}), 400
        player_name = player_row[1] or player_email.split('@')[0]
        
        # Déterminer task_name et task_points selon le type
        # ✅ FORCER l'utilisation du task_name envoyé par le frontend
        
        _dbg(f"\n📋 [TASK NAME DEBUG]")
        _dbg(f"   task_name_from_payload = '{task_name_from_payload}'")
        
        if task_type == 'custom':
            # Tâche personnalisée
            c.execute("SELECT task_name, points FROM custom_tasks WHERE id=? AND house_id=?", (task_id, user_house_id))
            task_row = c.fetchone()
            if not task_row:
                return jsonify({'success': False, 'error': 'Tâche non trouvée'}), 404
            task_points = task_row[1] or 10
            # Utiliser le nom du payload, sinon celui de la DB
            task_name = task_name_from_payload if task_name_from_payload else task_row[0]
        else:
            # Tâche standard
            normalized_cat = normalize_category(category)
            if normalized_cat not in TASKS_CONFIG or int(task_id) < 0 or int(task_id) >= len(TASKS_CONFIG.get(normalized_cat, [])):
                return jsonify({'success': False, 'error': 'Tâche introuvable'}), 404
            task = TASKS_CONFIG[normalized_cat][int(task_id)]
            task_points = task.get('points', 10)
            # Utiliser le nom du payload, sinon celui de TASKS_CONFIG
            task_name = task_name_from_payload if task_name_from_payload else task.get('name')
            # Appliquer multiplicateur si chambre bébé
            if normalized_cat == 'chambre_bebe':
                task_points = int(task_points * 1.5)
        
        _dbg(f"   📌 FINAL task_name = '{task_name}'")
        _dbg(f"📋 [END DEBUG]\n")
        
        today = date.today().isoformat()
        
        # 🍼 Tâches bébé : aucune restriction (biberon, couche, dormir bébé...)
        baby_unlimited_tasks = [
            'biberon', 'couche', 'couches', 'dormir', 'donner le biberon', 'changer les couches'
        ]
        is_baby_unlimited = any(kw.lower() in task_name.lower() for kw in baby_unlimited_tasks)
        
        # 🍳 Tâches cuisine : max 2 fois par jour
        is_kitchen_task = 'cuisine' in (category or '').lower()
        
        # 🔍 LOG DEBUG : Vérifier le nom de la tâche utilisé
        _dbg(f"\n🔍 [DOUBLON CHECK] Avant vérification:")
        _dbg(f"   - task_name utilisé: '{task_name}'")
        _dbg(f"   - category: '{category}'")
        _dbg(f"   - player_email: '{player_email}'")
        _dbg(f"   - today: '{today}'")
        _dbg(f"   - is_baby_unlimited: {is_baby_unlimited}")
        _dbg(f"   - is_kitchen_task: {is_kitchen_task}")
        
        if is_baby_unlimited:
            pass  # Aucune restriction pour les tâches bébé
        elif is_kitchen_task:
            c.execute("SELECT COUNT(*) FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at)=?",
                     (player_email, category, task_name, today))
            if c.fetchone()[0] >= 2:
                display_task_name = task_name_from_payload if task_name_from_payload else task_name
                funny_messages = [
                    f"🍳 '{display_task_name}' c'est la 3ème fois ! Max 2 fois par jour en cuisine 😅",
                    f"⚡ Wow ! '{display_task_name}' déjà 2 fois aujourd'hui ! Repose-toi ! 💪",
                    f"🏆 '{display_task_name}' × 2 c'est déjà super ! On s'arrête là 😊",
                ]
                funny_message = random.choice(funny_messages)
                _dbg(f"   Message envoyé (cuisine max 2): '{funny_message}'")
                return jsonify({'success': False, 'error': funny_message, 'duplicate': True}), 200
        else:
            c.execute("SELECT id FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at)=?", 
                     (player_email, category, task_name, today))
            result = c.fetchone()
            
            if result:
                # ✅ UTILISER UNIQUEMENT le task_name du PAYLOAD pour le message
                # C'est le nom RÉEL de la tâche affichée à l'utilisateur
                display_task_name = task_name_from_payload if task_name_from_payload else task_name
                
                _dbg(f"\n🚨🚨🚨 DOUBLON DÉTECTÉ 🚨🚨🚨")
                _dbg(f"   task_name_from_payload: '{task_name_from_payload}'")
                _dbg(f"   task_name (config): '{task_name}'")
                _dbg(f"   display_task_name utilisé: '{display_task_name}'")
                _dbg(f"🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨\n")
                
                # 🎭 Messages humoristiques avec le vrai nom de la tâche
                funny_messages = [
                    f"✅ Tu as déjà validé '{display_task_name}' aujourd'hui ! Une fois suffit 😊",
                    f"🎯 '{display_task_name}' c'est fait ! Passe à autre chose champion(ne) ! 💪",
                    f"⚡ '{display_task_name}' déjà validé ! Tu es tellement efficace que tu oublies ce que tu as fait 😄",
                    f"🏆 '{display_task_name}' : CHECK ! Pas besoin de le refaire, promis !",
                    f"😎 Relax ! '{display_task_name}' est déjà dans ta liste de victoires du jour !",
                    f"🔄 '{display_task_name}' ? Encore ? Tu l'as déjà fait aujourd'hui ! 😅",
                    f"🌟 Woah ! '{display_task_name}' a déjà été validé. Tu veux un trophée ? 🏅",
                    f"🎪 C'est pas Groundhog Day ! '{display_task_name}' est déjà coché ✓",
                ]
                
                funny_message = random.choice(funny_messages)
                _dbg(f"   Message envoyé: '{funny_message}'")
                return jsonify({'success': False, 'error': funny_message, 'duplicate': True}), 200
        
        # Insérer la tâche complétée
        c.execute("INSERT INTO completed_tasks (user_email, house_id, category, task_name, points, completed_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                 (player_email, user_house_id, category, task_name, task_points))
        c.execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE email=?", (task_points, player_email))

        # 🟠 Éteindre la pastille de la pièce : marquer les task_added de cette catégorie comme lus
        # Pour les enfants sans téléphone : marquer aussi pour le parent connecté (session['user'])
        try:
            normalized_cat_done = normalize_category(category) if category else None
            if normalized_cat_done:
                # Marquer comme lu pour le joueur ET pour l'utilisateur connecté (parent)
                _emails_to_mark = {player_email, session['user']}
                for _email_mark in _emails_to_mark:
                    c.execute("""
                        SELECT m.id FROM messages m
                        WHERE m.house_id = ? AND m.message_type = 'task_added'
                        AND m.related_category = ?
                        AND NOT EXISTS (
                            SELECT 1 FROM message_reads mr
                            WHERE mr.message_id = m.id AND mr.user_email = ?
                        )
                    """, (user_house_id, normalized_cat_done, _email_mark))
                    for _msg_row in c.fetchall():
                        c.execute("""
                            INSERT INTO message_reads (message_id, user_email)
                            VALUES (?, ?) ON CONFLICT(message_id, user_email) DO NOTHING
                        """, (_msg_row[0], _email_mark))
        except Exception as _e_badge:
            _dbg(f"⚠️ Erreur extinction pastille pièce: {_e_badge}")
        
        # Augmenter la santé de la maison
        try:
            c.execute("SELECT health FROM houses WHERE id=?", (user_house_id,))
            hrow = c.fetchone()
            current_health = hrow[0] if hrow and hrow[0] is not None else 0
            new_health = min(current_health + 1, 100)
            c.execute("UPDATE houses SET health=? WHERE id=?", (new_health, user_house_id))
        except Exception:
            pass
        
        # Variable pour suivre si un message baby_tracking a été créé
        baby_tracking_created = False
        
        # Baby tracking si applicable
        _dbg(f"🔍 DEBUG BABY TRACKING - tracking_time={tracking_time}, category={category}, task_name={task_name}")
        
        # Vérifier si c'est une tâche bébé par le nom de la tâche (plus fiable)
        is_baby_task = task_name and ('biberon' in task_name.lower() or 'couche' in task_name.lower() or 'dormir' in task_name.lower())
        
        if tracking_time and is_baby_task:
            _dbg(f"✅ Condition baby tracking remplie!")
            try:
                task_type_baby = None
                if 'biberon' in task_name.lower():
                    task_type_baby = 'biberon'
                elif 'couche' in task_name.lower():
                    task_type_baby = 'couches'
                elif 'dormir' in task_name.lower():
                    task_type_baby = 'sommeil'
                
                _dbg(f"🔍 Type détecté: {task_type_baby}")
                
                if task_type_baby:
                    # Sauvegarder dans baby_tracking
                    c.execute("""
                        INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (player_email, user_house_id, task_type_baby, tracking_time, bottle_ml if bottle_ml else None, observations))
                    
                    _dbg(f"✅ Baby tracking sauvegardé: {player_name} - {task_type_baby} - {tracking_time}")
                    
                    # Créer le message pour la messagerie
                    if task_type_baby == 'biberon':
                        ml_text = f" ({bottle_ml} ml)" if bottle_ml else ""
                        message_text = f"🍼 {player_name} a donné le biberon à {tracking_time}{ml_text}"
                        if observations:
                            message_text += f"\n📝 {observations}"
                    elif task_type_baby == 'couches':
                        message_text = f"👶 {player_name} a changé les couches à {tracking_time}"
                        if observations:
                            message_text += f"\n📝 {observations}"
                    else:  # sommeil
                        message_text = f"😴 {player_name} a couché bébé à {tracking_time}"
                        if observations:
                            message_text += f"\n📝 {observations}"
                    
                    _dbg(f"📬 Création message baby_tracking: house_id={user_house_id}, sender={player_email}")
                    _dbg(f"📬 Contenu du message: {message_text[:100]}...")
                    
                    # ✅ Créer le message directement dans la transaction courante pour éviter les pertes
                    from datetime import datetime
                    c.execute("""
                        INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, timestamp)
                        VALUES (?, ?, 'house', ?, 'baby_tracking', ?)
                    """, (user_house_id, player_email, message_text, datetime.now().isoformat()))
                    message_id = c.lastrowid
                    _dbg(f"✅ Message baby_tracking créé avec ID: {message_id}")
                    
                    # 🔌 Marquer pour synchroniser la messagerie plus tard (après le commit)
                    baby_tracking_created = True
                    
            except Exception as e:
                _dbg(f"⚠️ Erreur baby tracking: {e}")
                import traceback
                traceback.print_exc()
        else:
            pass
        
        # ✅ Marquer tous les messages task_added non lus comme lus pour ce joueur
        # (il a validé une mission → le rappel peut s'éteindre)
        try:
            c.execute("""
                SELECT m.id FROM messages m
                WHERE m.house_id = ? AND m.message_type = 'task_added'
                AND NOT EXISTS (
                    SELECT 1 FROM message_reads mr
                    WHERE mr.message_id = m.id AND mr.user_email = ?
                )
            """, (user_house_id, player_email))
            for msg_row in c.fetchall():
                c.execute("""
                    INSERT INTO message_reads (message_id, user_email)
                    VALUES (?, ?) ON CONFLICT(message_id, user_email) DO NOTHING
                """, (msg_row[0], player_email))
        except Exception:
            pass

        # ✅ COMMIT en premier pour que les données soient disponibles pour les autres clients
        conn.commit()
        
        # 🔌 WebSocket notification - APRÈS le commit pour que les autres clients voient les nouvelles données
        _dbg(f"🔍 DEBUG WebSocket: SOCKETIO_AVAILABLE={SOCKETIO_AVAILABLE}, socketio={socketio is not None}")
        if SOCKETIO_AVAILABLE and socketio:
            _dbg(f"🚀 Tentative d'envoi WebSocket pour house_id={user_house_id}, player={player_email}")
            try:
                # Rouvrir une connexion pour récupérer les données à jour
                conn_ws = get_db_connection()
                c_ws = conn_ws.cursor()
                c_ws.execute("""
                    SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
                           COALESCE(SUM(ct.points), 0) as daily_points
                    FROM users u
                    LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                        AND DATE(ct.completed_at) = DATE('now')
                    WHERE u.house_id = ?
                    GROUP BY u.email, u.name, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style, u.points
                    ORDER BY daily_points DESC, u.points DESC
                """, (user_house_id,))
                players_data = []
                for p in c_ws.fetchall():
                    players_data.append({
                        'email': p[0], 'name': p[1], 'avatar': p[2],
                        'avatar_url': p[3], 'avatar_file': p[4],
                        'total_points': p[5] or 0, 'daily_points': int(p[6]) if p[6] else 0
                    })
                conn_ws.close()
                
                _dbg(f"📊 Données récupérées: {len(players_data)} joueurs")
                for p in players_data:
                    _dbg(f"   - {p['name']}: {p['daily_points']} pts (total: {p['total_points']})")
                
                # 📡 Émettre la mise à jour à tous les joueurs de la maison
                room_name = f'house_{user_house_id}'
                _dbg(f"📡 Émission WebSocket vers room='{room_name}', namespace='/'")
                _dbg(f"   Joueurs dans la room : {len(players_data)}")
                _dbg(f"   🔍 DEBUG: socketio object = {socketio}")
                _dbg(f"   🔍 DEBUG: SOCKETIO_AVAILABLE = {SOCKETIO_AVAILABLE}")
                
                # Utiliser safe_socketio_emit() pour gérer les sessions invalides
                safe_socketio_emit('players_points_update', {
                    'players': players_data, 'updated_player': player_email
                }, namespace='/', room=room_name, broadcast=True)
                
                _dbg(f"✅ WebSocket: Notification envoyée pour {player_email} (+{task_points} pts)")
                _dbg(f"   Payload envoyé: {len(players_data)} joueurs, updated_player={player_email}")
                
                # 🔌 Synchroniser la messagerie si un message baby_tracking a été créé
                if baby_tracking_created:
                    safe_socketio_emit('messages_list_update', {
                        'house_id': user_house_id,
                        'action': 'baby_tracking',
                        'sender_email': player_email,
                        'sender_name': player_name
                    }, namespace='/', room=room_name, broadcast=True)
                    _dbg(f"🔌 WebSocket: Synchronisation messagerie baby_tracking pour house_{user_house_id}")
                    
            except Exception as ws_err:
                _dbg(f"⚠️ Erreur WebSocket: {ws_err}")
                import traceback
                traceback.print_exc()
        else:
            _dbg(f"⚠️ WebSocket NON DISPONIBLE - notification non envoyée")
        
        return jsonify({
            'success': True,
            'points': task_points,
            'player_email': player_email,
            'player_name': player_name,
            'task_name': task_name,
            'timestamp': int(time.time())
        })
        
    except Exception as e:
        conn.rollback()
        _dbg(f"❌ Erreur validation AJAX: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# �🎭 API : Récupérer la liste des avatars disponibles
@app.route('/api/avatars')
def api_avatars():
    """
    Retourne la liste de tous les avatars disponibles :
    - Images PNG du dossier static/avatars
    - Emojis configurés dans avatars_config.json
    """
    import json
    
    result = {
        'images': [],
        'categories': []
    }
    
    # 1. Lister les fichiers PNG du dossier avatars
    avatars_folder = os.path.join(app.static_folder, 'avatars')
    try:
        for filename in os.listdir(avatars_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                # Exclure les photos uploadées (UUID) et les fichiers de config
                if '-' in filename and len(filename) > 30:
                    continue  # C'est probablement une photo uploadée (UUID)
                if filename == 'avatars_config.json':
                    continue
                    
                result['images'].append({
                    'file': filename,
                    'url': url_for('static', filename=f'avatars/{filename}'),
                    'label': filename.replace('.png', '').replace('.jpg', '').replace('_', ' ').replace('.jpeg', '').title()
                })
    except Exception as e:
        _dbg(f"Erreur lecture dossier avatars: {e}")
    
    # 2. Charger la config des emojis si elle existe
    config_path = os.path.join(avatars_folder, 'avatars_config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ne garder que les catégories emoji (pas les images car on les a déjà)
                emoji_categories = [cat for cat in config.get('categories', []) if cat.get('type') == 'emoji']
                result['categories'] = emoji_categories
        except Exception as e:
            _dbg(f"Erreur lecture config avatars: {e}")
    
    return result, 200


# 🎯 NOUVELLE ROUTE API : Récupérer les tâches validées aujourd'hui
@app.route('/api/daily_tasks')
def api_daily_tasks():
    """
    Retourne les tâches validées aujourd'hui avec heure, joueur, points
    Format JSON pour affichage dans le dashboard
    """
    if 'user' not in session:
        return {'tasks': []}, 200
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Récupérer house_id de l'utilisateur courant
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'tasks': []}, 200
        
        house_id = row[0]
        
        # Filtrer sur "aujourd'hui" en heure de Paris (Render tourne en UTC)
        from datetime import date, datetime, timezone
        try:
            from zoneinfo import ZoneInfo
            paris_tz = ZoneInfo('Europe/Paris')
        except ImportError:
            try:
                import pytz
                paris_tz = pytz.timezone('Europe/Paris')
            except ImportError:
                paris_tz = None

        now_paris = datetime.now(paris_tz) if paris_tz else datetime.now()
        today_local = now_paris.date()

        c.execute("""
            SELECT 
                ct.user_email, 
                ct.task_name, 
                ct.points, 
                ct.completed_at,
                ct.category,
                u.name,
                u.avatar_url,
                u.avatar_file,
                u.avatar,
                u.avatar_style
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ?
              AND u.house_id = ?
              AND (ct.category IS NULL OR ct.category NOT IN ('bonus', 'malus'))
            ORDER BY ct.completed_at DESC
            LIMIT 300
        """, (house_id, house_id))
        
        rows = c.fetchall()
        raw_tasks = []

        for row in rows:
            email, task_name, points, completed_at, category, name, avatar_url, avatar_file, avatar_seed, avatar_style = row
            
            # Résoudre l'avatar
            final_avatar = None
            valid_file = validate_avatar_file(avatar_file)
            if valid_file:
                final_avatar = url_for('static', filename=f'avatars/{valid_file}', _external=True)
            elif avatar_url and avatar_url.startswith('http'):
                final_avatar = avatar_url
            else:
                seed = avatar_seed or (name or email.split('@')[0])
                style = avatar_style or 'adventurer'
                final_avatar = f'https://api.dicebear.com/7.x/{style}/svg?seed={seed}'
            
            # Convertir completed_at en heure de Paris
            completed_date = None
            time_str = '??:??'
            try:
                if hasattr(completed_at, 'strftime'):
                    dt = completed_at
                    if not getattr(dt, 'tzinfo', None):
                        dt = dt.replace(tzinfo=timezone.utc)
                    if paris_tz:
                        dt = dt.astimezone(paris_tz)
                    completed_date = dt.date()
                    time_str = dt.strftime('%H:%M')
                else:
                    s = str(completed_at or '')
                    dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
                    if not dt.tzinfo:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if paris_tz:
                        dt = dt.astimezone(paris_tz)
                    completed_date = dt.date()
                    time_str = dt.strftime('%H:%M')
            except Exception:
                try:
                    s = str(completed_at or '')
                    if ' ' in s:
                        dt = datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
                    elif 'T' in s:
                        dt = datetime.fromisoformat(s[:19])
                    else:
                        dt = None
                    if dt:
                        # timestamp sans tz = UTC stocké sur Render → convertir
                        dt = dt.replace(tzinfo=timezone.utc)
                        if paris_tz:
                            dt = dt.astimezone(paris_tz)
                        completed_date = dt.date()
                        time_str = dt.strftime('%H:%M')
                except Exception:
                    pass

            # Ne garder que les tâches du jour (heure de Paris)
            if completed_date != today_local:
                continue
            
            raw_tasks.append({
                'player_name': name if name else email.split('@')[0],
                'player_email': email,
                'task_name': task_name,
                'points': points or 0,
                'time': time_str,
                'avatar': final_avatar,
                'is_current_user': (email == session['user']),
                'category': category or ''
            })

        # Regrouper les entrées 'courses' par joueur en une seule ligne
        # (chaque article coché génère +1 pt → on affiche "🛒 Courses (N articles) : X pts")
        tasks = []
        courses_by_player = {}  # {email: {points, time, player_name, avatar, is_current_user}}
        for t in raw_tasks:
            if t['category'] == 'courses':
                key = t['player_email']
                if key not in courses_by_player:
                    courses_by_player[key] = {
                        'player_name': t['player_name'],
                        'player_email': t['player_email'],
                        'avatar': t['avatar'],
                        'is_current_user': t['is_current_user'],
                        'time': t['time'],
                        'points': 0,
                        'count': 0
                    }
                courses_by_player[key]['points'] += t['points']
                courses_by_player[key]['count'] += 1
            else:
                tasks.append(t)

        # Insérer une ligne résumée pour les courses de chaque joueur
        for key, c_data in courses_by_player.items():
            n = c_data['count']
            label = f"🛒 Courses ({n} article{'s' if n > 1 else ''})"
            tasks.append({
                'player_name': c_data['player_name'],
                'player_email': c_data['player_email'],
                'task_name': label,
                'points': c_data['points'],
                'time': c_data['time'],
                'avatar': c_data['avatar'],
                'is_current_user': c_data['is_current_user'],
                'category': 'courses'
            })

        # Trier par heure décroissante et limiter à 15
        tasks.sort(key=lambda x: x['time'], reverse=True)
        tasks = tasks[:15]

        return {'tasks': tasks}, 200
        
    except Exception as e:
        _dbg(f"Erreur API daily_tasks: {e}")
        return {'tasks': [], 'error': str(e)}, 500
    finally:
        conn.close()


@app.route('/test_player_selector')
def test_player_selector():
    """Page de test pour le sélecteur de joueurs"""
    return render_template('test_player_selector.html')


@app.route('/api/players_points')
def api_players_points():
    """
    API pour récupérer les points de tous les joueurs de la maison en temps réel.
    Utilisé pour mettre à jour automatiquement l'affichage sans rafraîchir la page.
    """
    if 'user' not in session:
        return {'players': []}, 200
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Récupérer house_id de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'players': []}, 200
        
        house_id = row[0]
        
        # Récupérer les points de tous les joueurs avec get_house_players_points
        players = get_house_players_points(house_id)
        
        # Formater pour la réponse API
        players_data = []
        for p in players:
            players_data.append({
                'email': p['email'],
                'name': p['name'],
                'avatar': p.get('avatar'),
                'avatar_url': p.get('avatar_url'),
                'avatar_file': p.get('avatar_file'),
                'points': p['points'],
                'daily_points': p.get('daily_points', 0),
                'daily_tasks': p.get('daily_tasks', 0)
            })
        
        # Récupérer la santé de la maison
        c.execute("SELECT health FROM houses WHERE id=?", (house_id,))
        health_row = c.fetchone()
        house_health = health_row[0] if health_row and health_row[0] is not None else 100
        
        resp = jsonify({'players': players_data, 'house_health': house_health})
        resp.headers['Cache-Control'] = 'no-store'
        return resp, 200
        
    except Exception as e:
        _dbg(f"Erreur API players_points: {e}")
        return {'players': [], 'error': str(e)}, 500
    finally:
        conn.close()



@app.route('/api/weekly_stats')
def api_weekly_stats():
    """
    API pour les stats hebdomadaires de tous les joueurs.
    Utilisé par le widget classement du bas dans menu.html
    """
    if 'user' not in session:
        return jsonify({'players': []}), 200

    from datetime import date, timedelta
    conn = get_db_connection()
    c = conn.cursor()

    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify({'players': []}), 200

        house_id = row[0]

        # Lundi de la semaine en cours
        today = date.today()
        monday = (today - timedelta(days=today.weekday())).isoformat()

        players = get_house_players_points(house_id)

        players_data = []
        for p in players:
            email = p['email']
            c.execute("""
                SELECT COALESCE(SUM(points), 0), COUNT(*)
                FROM completed_tasks
                WHERE user_email=? AND house_id=? AND DATE(completed_at) >= ?
            """, (email, house_id, monday))
            row_w = c.fetchone()
            weekly_points = int(row_w[0]) if row_w and row_w[0] else 0
            weekly_tasks  = int(row_w[1]) if row_w and row_w[1] else 0

            players_data.append({
                'email': email,
                'name': p['name'],
                'avatar_url': p.get('avatar_url') or '',
                'avatar_file': p.get('avatar_file') or '',
                'daily_points': p.get('daily_points', 0),
                'weekly_points': weekly_points,
                'weekly_tasks': weekly_tasks,
                'total_points': p.get('points', 0),
                'player_color_hex': p.get('player_color_hex') or '',
            })

        players_data.sort(key=lambda x: x['weekly_points'], reverse=True)

        resp = jsonify({'players': players_data})
        resp.headers['Cache-Control'] = 'no-store'
        return resp, 200

    except Exception as e:
        _dbg(f"Erreur api_weekly_stats: {e}")
        return jsonify({'players': [], 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/unread_counts')
def api_unread_counts():
    """
    API pour récupérer les compteurs de messages non lus en temps réel.
    Utilisé pour mettre à jour les badges sans rafraîchir la page.
    """
    if 'user' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer house_id
        c.execute('SELECT house_id FROM users WHERE email = ?', (session['user'],))
        user_row = c.fetchone()
        
        if not user_row or not user_row[0]:
            conn.close()
            return jsonify({'error': 'Maison introuvable'}), 404
        
        house_id = user_row[0]
        
        # Récupérer les compteurs
        unread_received = get_unread_message_count(session['user'], house_id)
        unread_by_sender = get_unread_messages_by_sender(session['user'], house_id)
        unread_sent_to = get_unread_messages_sent_to(session['user'], house_id)
        children_unread = get_children_unread_counts(house_id)
        unread_baby = get_unread_count_by_type(session['user'], house_id, 'baby_tracking', include_own=True)
        unread_task_added = get_unread_count_by_type(session['user'], house_id, 'task_added')
        unread_courses_added = get_unread_count_by_type(session['user'], house_id, 'courses_added')

        # 🛒 Articles non cochés dans la liste de courses
        courses_pending_count = 0
        try:
            c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (house_id,))
            courses_pending_count = c.fetchone()[0] or 0
        except Exception:
            pass
        
        conn.close()
        
        resp = jsonify({
            'unread_received': unread_received,
            'unread_by_sender': unread_by_sender,
            'unread_sent_to': unread_sent_to,
            'children_unread': children_unread,
            'unread_baby': unread_baby,
            'unread_task_added': unread_task_added,
            'unread_courses_added': unread_courses_added,
            'courses_pending_count': courses_pending_count
        })
        resp.headers['Cache-Control'] = 'no-store'
        return resp, 200
        
    except Exception as e:
        _dbg(f"❌ Erreur API unread_counts: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/rooms_with_missions')
def api_rooms_with_missions():
    """
    API pour récupérer les pièces avec missions non validées.
    Utilisé pour mettre à jour les pastilles oranges en temps réel.
    """
    if 'user' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT house_id FROM users WHERE email = ?', (session['user'],))
        user_row = c.fetchone()
        if not user_row or not user_row[0]:
            conn.close()
            return jsonify({'rooms': []})
        house_id = user_row[0]
        c.execute("""
            SELECT ct.category, COUNT(*) as pending_count
            FROM custom_tasks ct
            WHERE ct.house_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM completed_tasks ctd
                WHERE ctd.house_id = ct.house_id
                AND ctd.category = ct.category
                AND ctd.completed_at >= ct.created_at
            )
            GROUP BY ct.category
        """, (house_id,))
        rooms = {row[0]: row[1] for row in c.fetchall()}
        conn.close()
        return jsonify({'rooms': rooms})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 🔔 ========== ROUTES API PUSH NOTIFICATIONS ==========

@app.route('/api/push/subscribe', methods=['POST'])
def api_push_subscribe():
    """
    Enregistre une subscription push pour l'utilisateur courant.
    Attend un JSON avec: endpoint, keys.p256dh, keys.auth
    """
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401
    
    try:
        subscription_data = request.get_json()
        
        if not subscription_data or 'endpoint' not in subscription_data:
            return {'success': False, 'error': 'Données invalides'}, 400
        
        # Ajouter user agent pour debug
        subscription_data['userAgent'] = request.headers.get('User-Agent', '')
        
        success = save_push_subscription(session['user'], subscription_data)
        
        if success:
            return {'success': True, 'message': 'Subscription enregistrée'}, 200
        else:
            return {'success': False, 'error': 'Erreur sauvegarde'}, 500
            
    except Exception as e:
        _dbg(f"❌ Erreur API push subscribe: {e}")
        return {'success': False, 'error': str(e)}, 500


@app.route('/api/push/unsubscribe', methods=['POST'])
def api_push_unsubscribe():
    """
    Désactive une subscription push.
    Attend un JSON avec: endpoint
    """
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401
    
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return {'success': False, 'error': 'Endpoint manquant'}, 400
        
        success = deactivate_push_subscription(endpoint)
        
        if success:
            return {'success': True, 'message': 'Subscription désactivée'}, 200
        else:
            return {'success': False, 'error': 'Erreur désactivation'}, 500
            
    except Exception as e:
        _dbg(f"❌ Erreur API push unsubscribe: {e}")
        return {'success': False, 'error': str(e)}, 500


@app.route('/api/push/vapid-public-key')
def api_push_vapid_key():
    """
    Retourne la clé publique VAPID pour les subscriptions push.
    Supporte les formats normal et base64.
    """
    import base64
    
    # Essayer d'abord le format base64
    vapid_public_b64 = os.environ.get('VAPID_PUBLIC_KEY_B64', '')
    
    if vapid_public_b64:
        # Décoder depuis base64
        vapid_public_key = base64.b64decode(vapid_public_b64).decode('utf-8')
    else:
        # Utiliser le format normal
        vapid_public_key = os.environ.get('VAPID_PUBLIC_KEY', '')
    
    if not vapid_public_key:
        return {'error': 'VAPID key non configurée'}, 500
    
    return {'publicKey': vapid_public_key}, 200


@app.route('/api/push/test', methods=['POST'])
def api_push_test():
    """
    Route de test pour envoyer une notification push à l'utilisateur courant.
    """
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401
    
    try:
        subscriptions = get_user_push_subscriptions(session['user'])
        
        if not subscriptions:
            return {'success': False, 'error': 'Aucune subscription trouvée'}, 404
        
        notification_data = {
            'title': '🧹 Dust Test',
            'body': 'Vos notifications push fonctionnent correctement !',
            'icon': '/static/images/logo.png',
            'url': '/menu'
        }
        
        sent_count = 0
        for sub in subscriptions:
            if send_push_notification(sub, notification_data):
                sent_count += 1
        
        if sent_count > 0:
            return {'success': True, 'sent': sent_count}, 200
        else:
            return {'success': False, 'error': 'Échec envoi notifications'}, 500
            
    except Exception as e:
        _dbg(f"❌ Erreur API push test: {e}")
        return {'success': False, 'error': str(e)}, 500


# 🔔 ========== FIN ROUTES API PUSH NOTIFICATIONS ==========


# 💬 ========== ROUTES API RAPPELS ==========

@app.route('/api/reminders/settings', methods=['GET'])
def api_get_reminder_settings():
    """
    Récupère les paramètres de rappels de l'utilisateur.
    """
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401
    
    settings = get_user_reminder_settings(session['user'])
    return {'success': True, 'settings': settings}, 200


@app.route('/api/reminders/settings', methods=['POST'])
def api_update_reminder_settings():
    """
    Met à jour les paramètres de rappels de l'utilisateur.
    """
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401
    
    data = request.get_json()
    
    success = update_user_reminder_settings(
        user_email=session['user'],
        enabled=data.get('enabled'),
        frequency=data.get('frequency'),
        quiet_hours_start=data.get('quiet_hours_start'),
        quiet_hours_end=data.get('quiet_hours_end')
    )
    
    if success:
        return {'success': True}, 200
    else:
        return {'success': False, 'error': 'Erreur mise à jour'}, 500


@app.route('/api/reminders/test', methods=['POST'])
def api_test_reminder():
    """
    Envoie un rappel de test immédiat.
    """
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return {'success': False, 'error': 'Pas de maison'}, 400
        
        house_id = row[0]
        
        # Créer et envoyer un rappel test
        message_type = request.get_json().get('type', 'reminder_funny')
        reminder_id = create_reminder(house_id, message_type, scheduled_for=None)
        
        if reminder_id:
            # Envoyer immédiatement
            success = send_reminder(reminder_id)
            if success:
                return {'success': True, 'message': 'Rappel envoyé !'}, 200
        
        return {'success': False, 'error': 'Erreur création rappel'}, 500
        
    except Exception as e:
        _dbg(f"❌ Erreur test reminder: {e}")
        return {'success': False, 'error': str(e)}, 500


# 💬 ========== FIN ROUTES API RAPPELS ==========

# 👶 ========== ROUTES SUIVI BÉBÉ ==========

@app.route('/baby_tracking/<cat>/<int:task_id>')
def baby_tracking(cat, task_id):
    """Page de suivi pour les tâches de bébé (biberon, couches, sommeil)"""
    _dbg(f"👶 PAGE BABY_TRACKING accédée par {session.get('user', 'NON_CONNECTE')} pour task_id={task_id}")
    
    if 'user' not in session:
        flash("Connecte-toi pour utiliser le suivi bébé.", "warning")
        return redirect(url_for('login'))
    
    normalized_cat = normalize_category(cat)
    
    if normalized_cat not in TASKS_CONFIG or task_id < 0 or task_id >= len(TASKS_CONFIG.get(normalized_cat, [])):
        flash("Tâche introuvable.", "warning")
        return redirect(url_for('categorie', cat=cat))
    
    task = TASKS_CONFIG[normalized_cat][task_id]
    task_name = task.get('name')
    
    # Déterminer le type de tâche
    task_type = None
    if 'biberon' in task_name.lower():
        task_type = 'biberon'
    elif 'couche' in task_name.lower():
        task_type = 'couches'
    elif 'dormir' in task_name.lower() or 'sommeil' in task_name.lower():
        task_type = 'sommeil'
    
    if not task_type:
        flash("Cette tâche ne nécessite pas de suivi spécial.", "info")
        return redirect(url_for('task_enhanced', cat=cat, task_id=task_id))
    
    # Récupérer l'historique des 5 derniers enregistrements
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    house_id = row[0] if row else None
    
    history = []
    if house_id:
        c.execute("""
            SELECT user_email, tracking_time, bottle_ml, observations, 
                   datetime(created_at, 'localtime') as created_at
            FROM baby_tracking 
            WHERE house_id=? AND task_type=?
            ORDER BY created_at DESC 
            LIMIT 5
        """, (house_id, task_type))
        history = [dict(zip(['user_email', 'tracking_time', 'bottle_ml', 'observations', 'created_at'], row)) 
                   for row in c.fetchall()]
    
    conn.close()
    
    return render_template('baby_tracking.html', 
                         task_name=task_name,
                         task_type=task_type,
                         category=cat,
                         task_id=task_id,
                         history=history)

@app.route('/save_baby_tracking', methods=['POST'])
def save_baby_tracking():
    """Enregistre un suivi de tâche bébé et envoie un message au partenaire"""
    _dbg(f"🍼 SAVE_BABY_TRACKING appelé par {session.get('user', 'INCONNU')}")
    
    if 'user' not in session:
        flash("Connecte-toi pour utiliser le suivi bébé.", "warning")
        return redirect(url_for('login'))
    
    task_type = request.form.get('task_type')
    task_name = request.form.get('task_name')
    tracking_time = request.form.get('tracking_time')
    bottle_ml = request.form.get('bottle_ml')
    observations = request.form.get('observations', '')
    category = request.form.get('category')
    task_id = request.form.get('task_id')
    
    _dbg(f"📝 Données reçues: task_type={task_type}, time={tracking_time}, ml={bottle_ml}")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer house_id
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    house_id = row[0] if row else None
    
    if not house_id:
        flash("Erreur : maison introuvable.", "danger")
        conn.close()
        return redirect(url_for('menu'))
    
    # Enregistrer le suivi
    c.execute("""
        INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session['user'], house_id, task_type, tracking_time, bottle_ml, observations))
    
    # Récupérer le nom complet de l'utilisateur
    c.execute("SELECT name FROM users WHERE email=?", (session['user'],))
    name_row = c.fetchone()
    user_name = name_row[0] if name_row else session['user'].split('@')[0]
    
    if task_type == 'biberon':
        message_text = f"🍼 {user_name} a donné le biberon à {tracking_time}"
        if bottle_ml:
            message_text += f" ({bottle_ml} ml)"
        if observations:
            message_text += f"\n📝 {observations}"
    elif task_type == 'couches':
        message_text = f"👶 {user_name} a changé les couches à {tracking_time}"
        if observations:
            message_text += f"\n📝 {observations}"
    else:  # sommeil
        message_text = f"😴 {user_name} a couché bébé à {tracking_time}"
        if observations:
            message_text += f"\n📝 {observations}"
    
    conn.commit()
    conn.close()
    
    # Envoyer le message directement dans la base de données
    try:
        from datetime import datetime
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, timestamp)
            VALUES (?, ?, 'house', ?, 'baby_tracking', ?)
        """, (house_id, session['user'], message_text, datetime.now().isoformat()))
        
        message_id = c.lastrowid
        conn.commit()
        conn.close()
        
        _dbg(f"✅ Message baby_tracking créé avec ID: {message_id} pour {user_name}")
        
        # ✅ IMPORTANT : Marquer automatiquement comme "lu" pour l'auteur de l'action
        # L'auteur ne doit PAS voir de notification pour sa propre action
        mark_message_as_read(message_id, session['user'])
        _dbg(f"✅ Message baby_tracking ID {message_id} marqué comme lu pour l'auteur {session['user']}")
        
        # 🔌 Synchroniser la liste des messages pour tous les utilisateurs de la maison
        if SOCKETIO_AVAILABLE and socketio:
            safe_socketio_emit('messages_list_update', {
                'house_id': house_id,
                'action': 'baby_tracking',
                'sender_email': session['user'],
                'sender_name': user_name,
                'task_type': task_type
            }, room=f'house_{house_id}', namespace='/', broadcast=True)
            _dbg(f"🔌 WebSocket: Synchronisation messagerie baby_tracking pour house_{house_id}")
    except Exception as e:
        _dbg(f"❌ Erreur création message baby_tracking: {e}")
        import traceback
        traceback.print_exc()
    
    flash(f"✅ Suivi enregistré et partagé avec votre partenaire !", "success")
    
    # Valider aussi la tâche (ajouter les points)
    return redirect(url_for('task_enhanced', cat=category, task_id=task_id))

# 👶 ========== FIN ROUTES SUIVI BÉBÉ ==========

@app.route('/invitation_partner')
def invitation_partner():
    """Page d'invitation pour les partenaires avec QR Code"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Récupérer le code et le nom de la maison
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    
    house_code = None
    house_name = None
    if row and row[0]:
        c.execute("SELECT code, house_name, name FROM houses WHERE id=?", (row[0],))
        house_row = c.fetchone()
        if house_row:
            house_code = house_row[0]
            house_name = house_row[1] if house_row[1] else house_row[2]
    conn.close()
    
    if not house_code:
        flash("Aucune maison trouvée. Créez d'abord une maison.", "warning")
        return redirect(url_for('menu'))
    
    # Construire l'URL d'invitation
    join_url = f"{request.host_url}invite/{house_code}"
    
    return render_template('invitation_partner.html', 
                         house_code=house_code,
                         house_name=house_name,
                         join_url=join_url)


# ==========================================
# WEBSOCKET - SYNCHRONISATION TEMPS RÉEL
# ==========================================

if SOCKETIO_AVAILABLE:
    @socketio.on('connect')
    def handle_connect():
        """Connexion d'un client WebSocket"""
        _dbg(f'🔌 Client connecté: {request.sid}')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Déconnexion d'un client WebSocket"""
        _dbg(f'❌ Client déconnecté: {request.sid}')
    
    @socketio.on('join_house')
    def handle_join_house(data):
        """Un joueur rejoint la room de sa maison"""
        user_email = data.get('email')
        _dbg(f'📩 join_house reçu : email={user_email}, sid={request.sid}')
        
        if not user_email:
            _dbg(f'⚠️ join_house : email manquant !')
            return
        
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT house_id FROM users WHERE email=?", (user_email,))
            row = c.fetchone()
            conn.close()
            
            if row and row[0]:
                house_id = row[0]
                room = f"house_{house_id}"
                join_room(room)
                emit('joined_room', {'room': room, 'email': user_email})
                _dbg(f'✅ {user_email} (sid={request.sid}) a REJOINT la room {room}')
                _dbg(f'   🔍 Clients dans la room : utiliser socketio.server.manager.rooms pour voir')
            else:
                _dbg(f'⚠️ {user_email} : house_id introuvable !')
        except Exception as e:
            _dbg(f'❌ Erreur join_house pour {user_email}: {e}')
    
    @socketio.on('points_updated')
    def handle_points_updated(data):
        """Diffuser la mise à jour des points à tous les joueurs de la maison"""
        try:
            user_email = data.get('email')
            if not user_email:
                return
            
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT house_id FROM users WHERE email=?", (user_email,))
            row = c.fetchone()
            
            if row and row[0]:
                house_id = row[0]
                room = f"house_{house_id}"
                
                # Récupérer les points de tous les joueurs de la maison
                c.execute("""
                    SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
                           COALESCE(SUM(ct.points), 0) as daily_points
                    FROM users u
                    LEFT JOIN completed_tasks ct ON u.email = ct.user_email
                        AND DATE(ct.completed_at) = DATE('now')
                    WHERE u.house_id = ?
                    GROUP BY u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points
                    ORDER BY daily_points DESC, u.points DESC
                """, (house_id,))
                players = []
                for p in c.fetchall():
                    players.append({
                        'email': p[0],
                        'name': p[1],
                        'avatar': p[2],
                        'avatar_url': p[3],
                        'avatar_file': p[4],
                        'total_points': p[5] or 0,
                        'daily_points': int(p[6]) if p[6] else 0
                    })
                
                conn.close()
                
                # Diffuser à tous les clients de la room
                emit('players_points_update', {'players': players}, room=room)
                _dbg(f'📊 Points mis à jour pour la room {room}')
        except Exception as e:
            _dbg(f'❌ Erreur points_updated: {e}')
    
    @socketio.on('avatar_updated')
    def handle_avatar_updated(data):
        """Diffuser le changement d'avatar à tous les joueurs de la maison"""
        try:
            user_email = data.get('email')
            if not user_email:
                return
            
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT house_id, name, avatar, avatar_url, avatar_file FROM users WHERE email=?", (user_email,))
            row = c.fetchone()
            
            if row and row[0]:
                house_id = row[0]
                room = f"house_{house_id}"
                
                player_data = {
                    'email': user_email,
                    'name': row[1],
                    'avatar': row[2],
                    'avatar_url': row[3],
                    'avatar_file': row[4]
                }
                
                conn.close()
                
                # Diffuser à tous les clients de la room
                emit('player_avatar_update', player_data, room=room)
                _dbg(f'👤 Avatar mis à jour pour {user_email} dans la room {room}')
        except Exception as e:
            _dbg(f'❌ Erreur avatar_updated: {e}')


# 🏠 ========== ROUTES TEST MESSAGES MAISON ==========

@app.route('/test_house_encouragement')
def test_house_encouragement():
    """Route de test pour envoyer un message d'encouragement de la maison"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
        user_row = c.fetchone()
        conn.close()
        
        if not user_row or not user_row[0]:
            return jsonify({'success': False, 'error': 'Pas de maison'}), 400
        
        house_id = user_row[0]
        player_name = user_row[1] if user_row[1] else session['user'].split('@')[0]
        
        # Envoyer un message d'encouragement
        result = send_house_encouragement(house_id, player_name=player_name)
        
        return jsonify({'success': result, 'message': 'Message d\'encouragement envoyé !'})
    except Exception as e:
        _dbg(f"❌ Erreur test encouragement: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/test_house_sermon')
def test_house_sermon():
    """Route de test pour envoyer un sermon humoristique de la maison"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
        user_row = c.fetchone()
        conn.close()
        
        if not user_row or not user_row[0]:
            return jsonify({'success': False, 'error': 'Pas de maison'}), 400
        
        house_id = user_row[0]
        player_name = user_row[1] if user_row[1] else session['user'].split('@')[0]
        
        # Envoyer un sermon humoristique
        result = send_house_sermon(house_id, player_name=player_name, sermon_type='funny')
        
        return jsonify({'success': result, 'message': 'Sermon envoyé ! 😄'})
    except Exception as e:
        _dbg(f"❌ Erreur test sermon: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/test_house_sermon_lazy')
def test_house_sermon_lazy():
    """Route de test pour envoyer un sermon général d'inactivité"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_row = c.fetchone()
        conn.close()
        
        if not user_row or not user_row[0]:
            return jsonify({'success': False, 'error': 'Pas de maison'}), 400
        
        house_id = user_row[0]
        
        # Envoyer un sermon général
        result = send_house_sermon(house_id, sermon_type='lazy')
        
        return jsonify({'success': result, 'message': 'Sermon général envoyé ! 🏠'})
    except Exception as e:
        _dbg(f"❌ Erreur test sermon lazy: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 🏠 ========== FIN ROUTES TEST MESSAGES MAISON ==========


# ─── KEEP-ALIVE supprimé (plan payant Render → serveur toujours allumé) ──────


if __name__ == '__main__':
    # Affiche la table des routes au démarrage (utile pour debug)
    try:
        _dbg('\n--- Flask URL Map ---')
        for rule in app.url_map.iter_rules():
            _dbg(f"{rule.endpoint}: {rule}")
        _dbg('---------------------\n')
    except Exception:
        pass

    # Forcer le port 8000
    chosen_port = 8000
    print(f"Démarrage de Dust sur le port {chosen_port}...")
    print("⚠️  Mode développement : pour une meilleure stabilité, utilisez un serveur WSGI en production")
    
    # Démarrer avec SocketIO si disponible, sinon utiliser Flask standard
    if SOCKETIO_AVAILABLE and socketio:
        print("🔌 Démarrage avec WebSocket (SocketIO)")
        socketio.run(
            app,
            debug=True,
            host='0.0.0.0',
            port=chosen_port,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
    else:
        print("⚠️ Démarrage sans WebSocket")
        # Paramètres optimisés pour gérer plusieurs connexions
        app.run(
            debug=True, 
            host='0.0.0.0', 
            port=chosen_port, 
            use_reloader=False,
            threaded=True,  # Active le mode multi-thread
            request_handler=None  # Utilise le handler par défaut mais en mode thread
        )