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
from datetime import date, datetime, timedelta, timezone
import secrets
import os
import string
import base64
import uuid
import json
import requests
import time
import random

# ─── TIMEZONE EUROPE/PARIS ──────────────────────────────────────────────────
try:
    from zoneinfo import ZoneInfo
    PARIS_TZ = ZoneInfo('Europe/Paris')
except ImportError:
    try:
        import pytz
        PARIS_TZ = pytz.timezone('Europe/Paris')
    except ImportError:
        PARIS_TZ = None

def now_paris():
    """Retourne datetime.now() en heure de Paris (naive, sans tzinfo)."""
    if PARIS_TZ:
        dt = datetime.now(PARIS_TZ)
        return dt.replace(tzinfo=None)   # naive pour compatibilité DB
    return datetime.now()

def to_paris(dt_or_str):
    """Convertit un datetime ou une chaîne ISO en heure Paris.
    Depuis le fix timezone, PostgreSQL stocke déjà en heure Paris
    (SET timezone = 'Europe/Paris'), donc les naïves sont déjà correctes.
    Seuls les datetime aware (avec +00:00 / Z) sont convertis."""
    if dt_or_str is None:
        return None
    try:
        if isinstance(dt_or_str, str):
            dt_or_str = dt_or_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(dt_or_str)
        else:
            dt = dt_or_str
        # Si le datetime est aware (ex: chaîne avec +00:00), convertir en Paris
        if dt.tzinfo is not None and PARIS_TZ:
            dt = dt.astimezone(PARIS_TZ)
            return dt.replace(tzinfo=None)
        # Naive → déjà en heure Paris (PostgreSQL timezone=Europe/Paris ou SQLite local)
        return dt
    except Exception:
        return dt_or_str

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
# datetime('now', '-N unit') → (CURRENT_TIMESTAMP + INTERVAL '-N unit')
_RE_DATETIME_NOW_OFFSET = re.compile(
    r"datetime\s*\(\s*'now'\s*,\s*'([^']+)'\s*\)",
    re.IGNORECASE
)
# datetime(col, 'localtime') → col::timestamp  (strip 'localtime' for PG)
_RE_DATETIME_COL_LOCALTIME = re.compile(
    r"datetime\s*\(\s*([^(),']+?)\s*,\s*'localtime'\s*\)",
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
        # 3b) datetime('now', '-1 hour') → (CURRENT_TIMESTAMP + INTERVAL '-1 hour')
        sql = _RE_DATETIME_NOW_OFFSET.sub(r"(CURRENT_TIMESTAMP + INTERVAL '\1')", sql)
        # 3c) datetime(col, 'localtime') → col::timestamp
        sql = _RE_DATETIME_COL_LOCALTIME.sub(r'\1::timestamp', sql)
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
            sql_ret = sql + ' RETURNING id'
            try:
                self._cur.execute(sql_ret, params if params else ())
                row = self._cur.fetchone()
                self.lastrowid = row[0] if row else None
                self.rowcount = self._cur.rowcount
                return
            except Exception:
                try:
                    self._cur.connection.rollback()
                except Exception:
                    pass
                # Table sans colonne id — exécuter sans RETURNING
                try:
                    self._cur.execute(sql, params if params else ())
                    self.lastrowid = None
                    self.rowcount = self._cur.rowcount
                    return
                except Exception:
                    try:
                        self._cur.connection.rollback()
                    except Exception:
                        pass
                    raise
        try:
            self._cur.execute(sql, params if params else ())
        except Exception:
            if self._is_pg:
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

# Route pour supprimer une tâche personnalisée (à placer après la création de l'objet app)
def register_delete_custom_task_route(app):
    @app.route('/delete_custom_task/<int:task_id>/<cat>', methods=['POST'])
    def delete_custom_task(task_id, cat):
        if 'user' not in session:
            flash("Connecte-toi pour supprimer une mission.", "warning")
            return redirect(url_for('auth.login'))

        conn = get_db_connection()
        c = conn.cursor()
        # Vérifier que la tâche existe et que l'utilisateur est le créateur
        c.execute("SELECT task_image, created_by FROM custom_tasks WHERE id=?", (task_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            flash("Tâche personnalisée introuvable.", "danger")
            return redirect(url_for('tasks.categorie', cat=cat))
        task_image, created_by = row
        if created_by != session['user']:
            conn.close()
            flash("Tu ne peux supprimer que tes propres missions.", "danger")
            return redirect(url_for('tasks.categorie', cat=cat))

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
        return redirect(url_for('tasks.categorie', cat=cat))
from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date
import os
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

@app.after_request
def add_cache_headers(response):
    # Cache 1 an pour les images statiques
    if request.path.startswith('/static/images/'):
        response.cache_control.max_age = 31536000
        response.cache_control.public = True
        response.headers['Vary'] = 'Accept-Encoding'
    return response

# 🔥 Cache Jinja2 : activé en prod (économie RAM), désactivé en local (debug)
if os.environ.get('RENDER'):
    app.jinja_env.auto_reload = False
    app.jinja_env.cache_size = 400
else:
    app.jinja_env.auto_reload = True
    app.jinja_env.cache = {}

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

# 🚀 WhiteNoise : sert les fichiers statiques efficacement (gzip auto + cache immutable)
try:
    from whitenoise import WhiteNoise
    _static_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=_static_root, prefix='static/', max_age=31536000)
    print("✅ WhiteNoise activé - root:", _static_root)
except ImportError:
    print("⚠️ whitenoise non installé")

# Ajouter un filtre Jinja personnalisé pour index
@app.template_filter('index')
def list_index_filter(lst, value):
    """Retourne l'index d'une valeur dans une liste"""
    try:
        return lst.index(value)
    except (ValueError, AttributeError):
        return 0

@app.template_filter('thumb')
def thumb_filter(path):
    """Convertit un chemin image en chemin thumb : cuisine/cafe.png -> cuisine/thumbs/cafe.webp"""
    if not path or '/' not in path or path.startswith('data:'):
        return path
    parts = path.rsplit('/', 1)
    name = parts[1].rsplit('.', 1)[0] + '.webp'
    return parts[0] + '/thumbs/' + name

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
    'lavande':    'linear-gradient(135deg, #c7b8ea 0%, #8a6fbf 100%)',
    'ocean':      'linear-gradient(135deg, #0077b6 0%, #023e8a 100%)',
    'corail':     'linear-gradient(135deg, #ff6b6b 0%, #c0392b 100%)',
    'emeraude':   'linear-gradient(135deg, #2ecc71 0%, #1a7a42 100%)',
    'sunset':     'linear-gradient(135deg, #ff9a56 0%, #e84393 100%)',
    'lilas':      'linear-gradient(135deg, #dda0dd 0%, #9b59b6 100%)',
    'caramel':    'linear-gradient(135deg, #d4a056 0%, #8b5e2a 100%)',
    'glacier':    'linear-gradient(135deg, #e0f4ff 0%, #89c4e1 100%)',
    'tropique':   'linear-gradient(135deg, #00b894 0%, #006d5b 100%)',
    'cuivre':     'linear-gradient(135deg, #b87333 0%, #6d3a1a 100%)',
}

LIGHT_THEMES = {'bleu', 'sable', 'menthe', 'rose', 'peche', 'lavande', 'emeraude', 'lilas', 'glacier'}

# Couleur complémentaire de la barre de progression pour chaque thème
BAR_COLORS = {
    'marron':     '#5bb8d4',      # bleu clair (complémentaire du marron)
    'bleu':       '#c0392b',      # grenat
    'foret':      '#d45b7a',      # rose framboise
    'nuit':       '#c4a84d',      # or chaud
    'ardoise':    '#d4855b',      # corail
    'prune':      '#4dc48a',      # vert émeraude
    'sable':      '#9b59b6',      # violet profond
    'menthe':     '#bd5b7a',      # rose foncé
    'framboise':  '#4dd4a8',      # turquoise
    'rose':       '#4ecdc4',      # turquoise
    'peche':      '#6c5ce7',      # indigo vibrant
    'lavande':    '#d4a855',      # or chaud
    'ocean':      '#e84393',      # rose magenta
    'corail':     '#4dd4d4',      # cyan
    'emeraude':   '#d45ba0',      # rose magenta
    'sunset':     '#4dc4e8',      # bleu ciel
    'lilas':      '#7abd5b',      # vert pomme
    'caramel':    '#5bb8d4',      # bleu glacier
    'glacier':    '#e17055',      # brique vif
    'tropique':   '#d45bd4',      # fuchsia
    'cuivre':     '#33a5b8',      # bleu cyan
}

@app.context_processor
def inject_bg_theme():
    bg = BG_THEMES['ocean']
    theme_name = 'ocean'
    try:
        if 'user' in session:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT bg_theme FROM users WHERE email=?", (session['user'],))
            row = c.fetchone()
            conn.close()
            if row and row[0] and row[0] != 'bleu' and row[0] in BG_THEMES:
                theme_name = row[0]
                bg = BG_THEMES[theme_name]
    except Exception:
        pass
    is_light = theme_name in LIGHT_THEMES
    bar_color = BAR_COLORS.get(theme_name, '#FDAE54')
    return {'bg_gradient': bg, 'bg_theme_name': theme_name, 'bg_theme_light': is_light, 'week_bar_color': bar_color}

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

@app.template_filter('date_fr')
def date_fr_filter(value, format='long'):
    """
    Formate une date en français.
    format='long' → 'dim. 12 avril à 10:42'
    format='short' → '12/04/2026'
    format='day' → 'dimanche 12 avril'
    """
    JOURS = ['lundi','mardi','mercredi',
             'jeudi','vendredi','samedi','dimanche']
    MOIS = ['','janvier','février','mars','avril',
            'mai','juin','juillet','août',
            'septembre','octobre','novembre','décembre']

    if not value:
        return ''

    # Convertit string en datetime si nécessaire
    if isinstance(value, str):
        try:
            from datetime import datetime
            value = datetime.fromisoformat(value)
        except Exception:
            return value

    jour = JOURS[value.weekday()]
    jour_court = jour[:3] + '.'
    mois = MOIS[value.month]

    if format == 'long':
        return f"{jour_court} {value.day} {mois} à {value.strftime('%H:%M')}"
    elif format == 'short':
        return value.strftime('%d/%m/%Y')
    elif format == 'day':
        return f"{jour} {value.day} {mois}"

    return str(value)

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date
import os
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
        return redirect(url_for('menu') + '?nav=1')
    # Sinon, afficher la page de bienvenue
    return redirect(url_for('auth.welcome'))

# Configuration pour l'upload de fichiers
UPLOAD_FOLDER = 'static/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max

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
                conn = psycopg2.connect(_PG_URL, connect_timeout=10,
                                        options="-c timezone=Europe/Paris")
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
        raw.execute('PRAGMA cache_size=2000')
        raw.execute('PRAGMA temp_store=FILE')
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
        today = now_paris().date()
        current_week_start = (today - timedelta(days=today.weekday())).isoformat()  # Lundi de cette semaine
        
        # Récupérer la date de dernière réinitialisation hebdomadaire
        c.execute("SELECT last_weekly_reset_date FROM houses WHERE id=?", (house_id,))
        row = c.fetchone()
        
        last_weekly_reset = row[0] if row and row[0] else None
        
        # Si on n'a jamais fait de reset hebdomadaire, ou si le dernier reset date d'avant cette semaine
        if not last_weekly_reset or last_weekly_reset < current_week_start:
            # On est dans une nouvelle semaine, réinitialiser les statistiques
            
            # 🟠 D'abord supprimer les custom_tasks de la semaine précédente
            # (AVANT de supprimer les completed_tasks, sinon elles réapparaîtraient comme "en attente")
            c.execute("""
                DELETE FROM custom_tasks
                WHERE house_id = ? AND DATE(created_at) < ?
            """, (house_id, current_week_start))

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
            from PIL import Image, ImageOps
            import io as _io
            img = Image.open(_io.BytesIO(image_data))
            img = ImageOps.exif_transpose(img)
            img = img.convert('RGB')
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
    base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://clean-beat-app.onrender.com").rstrip("/") + "/"
    
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
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+lave+vaisselle+economie'
        },
        {
            'name': 'Passer l\'éponge',
            'image': 'cuisine/passer l\'eponge.webp',
            'description': 'Nettoie les surfaces et la table !',
            'points': 4,
            'fun_text': '🧽 Frotte, frotte ! On efface les traces du festin !',
            'ad_text': 'Change ton éponge toutes les semaines pour éviter les bactéries !',
            'ad_link': 'https://www.consoglobe.com/eponges-ecologiques-cg'
        },
        {
            'name': 'Nettoyer le plan de travail',
            'image': 'cuisine/nettoyer le plan de travil.webp',
            'description': 'Des plans de travail impeccables !',
            'points': 4,
            'fun_text': '✨ Un plan de travail nickel, c\'est la base d\'une cuisine pro !',
            'ad_text': 'Bicarbonate + citron = le combo magique pour dégraisser sans produits chimiques !',
            'ad_link': 'https://www.youtube.com/results?search_query=produits+menagers+naturels+bicarbonate'
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
            'ad_link': 'https://www.youtube.com/results?search_query=lessive+maison+ecologique+recette'
        },
        {
            'name': 'Sécher son linge',
            'image': 'buanderie/linge etendu.webp',
            'description': 'Étendre ou sécher le linge',
            'points': 3,
            'fun_text': '🌞 Le soleil est le meilleur sèche-linge !',
            'ad_text': 'Le séchage à l\'air libre préserve tes vêtements et économise de l\'énergie.',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+secher+linge+rapidement'
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
            'ad_link': 'https://www.youtube.com/results?search_query=marie+kondo+pliage+tiroir'
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
            'ad_link': 'https://www.youtube.com/results?search_query=nettoyer+toilettes+vinaigre+naturel'
        },
        {
            'name': 'Changer le rouleau de papier toilette',
            'image': 'wc/jeter_rouleaux.png',
            'description': '🧻 Tu peux jeter les rouleaux ou en faire des ronds de serviettes ! 😄',
            'points': 2,
            'fun_text': '🧻 Le héros silencieux de la maison !',
            'ad_text': 'Le saviez-vous ? Le papier recyclé est tout aussi doux et préserve 70% d\'eau à la fabrication.',
            'ad_link': 'https://www.youtube.com/results?search_query=papier+toilette+ecologique+choisir'
        },
        {
            'name': 'Relever la cuvette',
            'image': 'wc/relever la cuvette.Webp',
            'description': '🎯 Relève la lunette des toilettes… Bien viser ; essaye un peu pour voir ! 😉',
            'points': 1,
            'fun_text': '🚽 Un petit geste, un grand respect !',
            'ad_text': 'Astuce : un abattant WC à fermeture ralentie évite les claquements !',
            'ad_link': 'https://www.youtube.com/results?search_query=installer+abattant+wc+frein+chute'
        },
        {
            'name': 'Séjourner aux toilettes',
            'image': 'wc/séjourner aux toilettes.webp',
            'description': '📱 Eh oui, c\'est tentant de passer sa vie aux toilettes pour échapper aux corvées ! 😂',
            'points': -3,
            'fun_text': '📱 La bibliothèque préférée de la maison !',
            'ad_text': 'Un repose-pieds physiologique améliore le confort et la santé intestinale !',
            'ad_link': 'https://www.youtube.com/results?search_query=position+ideale+toilettes+sante'
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
            'ad_link': 'https://www.youtube.com/results?search_query=faire+son+lit+comme+un+hotel'
        },
        {
            'name': 'Ranger sa chambre',
            'image': 'chambre ados/ranger sa chambre.webp',
            'description': 'Une chambre bien rangée pour mieux dormir !',
            'points': 5,
            'fun_text': '✨ Une chambre rangée, c\'est un esprit apaisé !',
            'ad_text': 'La règle des 3 piles : à garder, à donner, à laver. En 10 min, ta chambre respire !',
            'ad_link': 'https://www.youtube.com/results?search_query=marie+kondo+rangement+placard'
        },
        {
            'name': 'Aérer sa chambre',
            'image': 'chambre ados/aérer sa chambre.webp',
            'description': 'Ouvre la fenêtre pour renouveler l\'air !',
            'points': 2,
            'fun_text': '💨 Un peu d\'air frais, ça fait du bien !',
            'ad_text': 'Aérer 10 minutes par jour réduit l\'humidité et améliore la qualité de ton sommeil !',
            'ad_link': 'https://www.youtube.com/results?search_query=bien+aerer+sa+chambre+conseils'
        },
        {
            'name': 'Mettre ses vêtements dans la corbeille',
            'image': 'chambre ados/mettre ses vetements dans le panier à linge.webp',
            'description': 'Ne laisse pas traîner tes vêtements sales !',
            'points': 2,
            'fun_text': '👕 Direction le panier à linge !',
            'ad_text': 'Un panier à linge bien placé = moins de vêtements par terre !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+gestion+linge+sale'
        },
        {
            'name': 'Vider sa corbeille',
            'image': 'chambre ados/vider sa corbeille à papier.webp',
            'description': 'Vide ta poubelle pour garder une chambre propre !',
            'points': 2,
            'fun_text': '🗑️ Hop, à la poubelle !',
            'ad_text': 'Une poubelle vide tous les 2-3 jours évite les mauvaises odeurs !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+reduire+dechets+chambre'
        },
        {
            'name': 'Faire ses devoirs',
            'image': 'chambre ados/Faire ses devoirs.webp',
            'description': 'Travaille sérieusement pour réussir !',
            'points': 8,
            'fun_text': '📚 Le savoir, c\'est le pouvoir !',
            'ad_text': 'La technique Pomodoro : 25 min de travail, 5 min de pause. Efficacité maximale !',
            'ad_link': 'https://www.youtube.com/results?search_query=technique+pomodoro+devoirs'
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
            'ad_link': 'https://www.youtube.com/results?search_query=marie+kondo+rangement+placard'
        },
        {
            'name': 'Faire son lit',
            'image': 'chambre ados/faire son lit.webp',
            'description': 'Fait un lit propre et bien rangé !',
            'points': 3,
            'fun_text': '🛏️ Un lit fait = une journée bien commencée !',
            'ad_text': 'Astuce hôtel : tire d\'abord le drap du dessous bien tendu, puis borde les côtés. Résultat pro en 2 min !',
            'ad_link': 'https://www.youtube.com/results?search_query=faire+son+lit+comme+un+hotel'
        },
        {
            'name': 'Aérer sa chambre',
            'image': 'chambre ados/aérer sa chambre.webp',
            'description': 'Ouvre la fenêtre pour renouveler l\'air !',
            'points': 2,
            'fun_text': '💨 Un peu d\'air frais, ça fait du bien !',
            'ad_text': 'Aérer 10 minutes par jour réduit l\'humidité et améliore la qualité de ton sommeil !',
            'ad_link': 'https://www.youtube.com/results?search_query=bien+aerer+sa+chambre+conseils'
        },
        {
            'name': 'Mettre ses vêtements dans la corbeille',
            'image': 'chambre ados/mettre ses vetements dans le panier à linge.webp',
            'description': 'Ne laisse pas traîner tes vêtements sales !',
            'points': 2,
            'fun_text': '👕 Direction le panier à linge !',
            'ad_text': 'Un panier à linge bien placé = moins de vêtements par terre !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+gestion+linge+sale'
        },
        {
            'name': 'Vider sa corbeille',
            'image': 'chambre ados/vider sa corbeille à papier.webp',
            'description': 'Vide ta poubelle pour garder une chambre propre !',
            'points': 2,
            'fun_text': '🗑️ Hop, à la poubelle !',
            'ad_text': 'Une poubelle vide tous les 2-3 jours évite les mauvaises odeurs !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+reduire+dechets+chambre'
        },
        {
            'name': 'Faire ses devoirs',
            'image': 'chambre ados/Faire ses devoirs.webp',
            'description': 'Travaille sérieusement pour réussir !',
            'points': 8,
            'fun_text': '📚 Le savoir, c\'est le pouvoir !',
            'ad_text': 'La technique Pomodoro : 25 min de travail, 5 min de pause. Efficacité maximale !',
            'ad_link': 'https://www.youtube.com/results?search_query=technique+pomodoro+devoirs'
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
            'ad_link': 'https://www.youtube.com/results?search_query=marie+kondo+rangement+salon'
        },
        {
            'name': 'Faire la poussière',
            'image': 'salon/faire la poussière.webp',
            'description': 'Enlever la poussière sur les meubles',
            'points': 3,
            'fun_text': '✨ Adieu la poussière, bonjour la propreté !',
            'ad_text': 'Chiffons microfibres magiques !',
            'ad_link': 'https://www.youtube.com/results?search_query=utiliser+chiffon+microfibre+menage'
        },
        {
            'name': 'Laver les sols',
            'image': 'salon/laver les sols.webp',
            'description': 'Nettoyer les sols du salon',
            'points': 5,
            'fun_text': '🧼 Des sols qui brillent de mille feux !',
            'ad_text': 'Serpillières et produits sols !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+laver+sols+rapidement'
        },
        {
            'name': 'Passer l\'aspirateur',
            'image': 'salon/Passer l\'aspirateur.webp',
            'description': 'Aspirer le salon pour un sol propre',
            'points': 5,
            'fun_text': '🌪️ La tornade du ménage passe par ici !',
            'ad_text': 'Aspirateurs performants en promo !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+passer+aspirateur+efficace'
        },
        {
            'name': 'Laver les vitres',
            'image': 'salon/laver les vitres.webp',
            'description': 'Nettoyer les vitres du salon',
            'points': 5,
            'fun_text': '🪟 La vue sera encore plus belle !',
            'ad_text': 'Produits vitres sans traces !',
            'ad_link': 'https://www.youtube.com/results?search_query=nettoyer+vitres+sans+traces+vinaigre'
        },
        {
            'name': 'Arroser les plantes',
            'image': 'salon/arroser les plantes.webp',
            'description': 'Prendre soin des plantes du salon',
            'points': 2,
            'fun_text': '🌱 Un peu d\'eau pour la jungle urbaine !',
            'ad_text': 'Arrosoirs design et pratiques !',
            'ad_link': 'https://www.youtube.com/results?search_query=arroser+plantes+interieur+conseils'
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
            'ad_link': 'https://www.youtube.com/results?search_query=faire+son+lit+comme+un+hotel'
        },
        {
            'name': 'Changer les draps',
            'image': 'chambre parent/changer les draps du lit.webp',
            'description': 'Renouveler le linge de lit',
            'points': 4,
            'fun_text': '🧺 Des draps frais pour de beaux rêves !',
            'ad_text': 'Draps confortables en promo !',
            'ad_link': 'https://www.youtube.com/results?search_query=changer+draps+rapidement+astuce'
        },
        {
            'name': 'Ranger ses vêtements',
            'image': 'chambre parent/ranger ses vetements.webp',
            'description': 'Ranger les vêtements dans l\'armoire',
            'points': 3,
            'fun_text': '👔 Une armoire bien organisée !',
            'ad_text': 'Organisateurs de placard !',
            'ad_link': 'https://www.youtube.com/results?search_query=marie+kondo+rangement+placard'
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
            'ad_link': 'https://www.youtube.com/results?search_query=brossage+dents+technique+dentiste'
        },
        {
            'name': 'Reboucher le dentifrice',
            'image': 'salle de bain/reboucher le dentifrice.webp',
            'description': 'Le dentifrice bien fermé',
            'points': 1,
            'fun_text': '🧴 Un tube bien fermé pour éviter le gaspillage !',
            'ad_text': 'Dentifrices pour toute la famille !',
            'ad_link': 'https://www.youtube.com/results?search_query=brossage+dents+technique+dentiste'
        },
        {
            'name': 'Nettoyer ses cheveux',
            'image': 'salle de bain/nettoyer les cheveux.webp',
            'description': 'Enlever les cheveux du lavabo',
            'points': 2,
            'fun_text': '💇 Plus de cheveux dans le lavabo !',
            'ad_text': 'Accessoires salle de bain !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+sechage+cheveux+sain'
        },
        {
            'name': 'Nettoyer ses poils de barbe',
            'image': 'salle de bain/nettoyer les poils de barbe.webp',
            'description': 'Nettoyer les poils de barbe du lavabo',
            'points': 2,
            'fun_text': '🪒 La barbe de trois jours se range !',
            'ad_text': 'Rasoirs et accessoires !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+rasage+sans+irritation'
        },
        {
            'name': 'Jeter les bouteilles vides',
            'image': 'salle de bain/jeter les bouteilles de savon vide. wepb.webp',
            'description': 'Vider les bouteilles vides',
            'points': 2,
            'fun_text': '♻️ Faire de la place pour les nouvelles !',
            'ad_text': 'Organisateurs salle de bain !',
            'ad_link': 'https://www.youtube.com/results?search_query=marie+kondo+salle+de+bain'
        },
        {
            'name': 'Éponger l\'eau par terre',
            'image': 'salle de bain/éponger le sol.webp',
            'description': 'Sécher l\'eau au sol',
            'points': 3,
            'fun_text': '💦 Plus de flaques pour éviter de glisser !',
            'ad_text': 'Tapis de bain absorbants !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+eviter+eau+salle+de+bain'
        }
    ],
    'garage': [
        {
            'name': 'Ranger les outils',
            'image': 'salon/Passer l\'aspirateur.webp',
            'description': 'Un garage bien organisé !',
            'points': 5,
            'ad_text': 'Solutions de rangement garage !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+rangement+garage+atelier'
        },
        {
            'name': 'Balayer le garage',
            'image': 'salon/Passer l\'aspirateur.webp',
            'description': 'Un garage propre !',
            'points': 4,
            'ad_text': 'Matériel de nettoyage !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+nettoyer+garage+rapidement'
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
            'ad_link': 'https://www.youtube.com/results?search_query=idees+gouter+sain+enfant'
        },
        {
            'name': 'Signer les mots',
            'image': 'bonus/signer les mots.webp',
            'description': 'Signer les mots de l\'école',
            'points': 2,
            'fun_text': '✍️ Les devoirs administratifs !',
            'ad_text': 'Fournitures scolaires !',
            'ad_link': 'https://www.youtube.com/results?search_query=technique+pomodoro+devoirs'
        },
        {
            'name': 'Aller aux réunions d\'école',
            'image': 'bonus/aller aux reunions d\'ecole.webp',
            'description': 'Participer aux réunions scolaires',
            'points': 5,
            'fun_text': '🏫 Le suivi scolaire c\'est essentiel !',
            'ad_text': 'Agendas pour parents !',
            'ad_link': 'https://www.youtube.com/results?search_query=organisation+parents+ecole+conseils'
        },
        {
            'name': 'Prendre les RDV médicaux',
            'image': 'bonus/prendre les rdv médicaux.webp',
            'description': 'Gérer les rendez-vous médicaux',
            'points': 3,
            'fun_text': '🏥 La santé avant tout !',
            'ad_text': 'Applications de santé !',
            'ad_link': 'https://www.youtube.com/results?search_query=organiser+rdv+medicaux+famille'
        },
        {
            'name': 'Organiser les anniversaires',
            'image': 'bonus/organiser les anniversaire.webp',
            'description': 'Préparer les fêtes d\'anniversaire',
            'points': 5,
            'fun_text': '🎉 Les anniversaires c\'est la fête !',
            'ad_text': 'Décorations d\'anniversaire !',
            'ad_link': 'https://www.youtube.com/results?search_query=organiser+anniversaire+enfant+idees'
        },
        {
            'name': 'Déclarer les impôts',
            'image': 'bonus/déclarer les impôts.webp',
            'description': 'Gérer les déclarations fiscales',
            'points': 6,
            'fun_text': '💰 Les devoirs citoyens !',
            'ad_text': 'Solutions de gestion administrative !',
            'ad_link': 'https://www.youtube.com/results?search_query=organiser+papiers+administratifs+impots'
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
            'ad_link': 'https://www.youtube.com/results?search_query=apprendre+enfant+faire+son+lit'
        },
        {
            'name': 'Ranger sa chambre',
            'image': 'chambre ados/Ranger sa chambre.webp',
            'description': 'Remettre de l\'ordre dans la chambre',
            'points': 4,
            'fun_text': '✨ Une chambre rangée c\'est une chambre heureuse !',
            'ad_text': 'Rangements pratiques pour chambre enfant !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+rangement+chambre+enfant'
        },
        {
            'name': 'Aérer sa chambre',
            'image': 'chambre ados/aérer sa chambre.webp',
            'description': 'Ouvrir la fenêtre pour renouveler l\'air',
            'points': 2,
            'fun_text': '💨 Un air frais pour bien dormir !',
            'ad_text': 'Purificateurs d\'air pour chambre !',
            'ad_link': 'https://www.youtube.com/results?search_query=bien+aerer+sa+chambre+conseils'
        },
        {
            'name': 'Mettre les vêtements dans le panier',
            'image': 'chambre ados/mettre ses vetements dans le panier à linge.webp',
            'description': 'Trier les vêtements sales',
            'points': 3,
            'fun_text': '👕 Droit au but, dans le panier !',
            'ad_text': 'Paniers à linge design !',
            'ad_link': 'https://www.youtube.com/results?search_query=apprendre+enfant+ranger+vetements'
        },
        {
            'name': 'Vider sa corbeille',
            'image': 'chambre ados/vider sa corbeille à papier.webp',
            'description': 'Vider la corbeille à papier',
            'points': 2,
            'fun_text': '🗑️ Poubelle vide, esprit clair !',
            'ad_text': 'Jolies corbeilles pour chambre !',
            'ad_link': 'https://www.youtube.com/results?search_query=astuce+rangement+enfant+jouets'
        },
        {
            'name': 'Faire ses devoirs',
            'image': 'chambre ados/Faire ses devoirs.webp',
            'description': 'Faire les devoirs du soir',
            'points': 5,
            'fun_text': '📚 Les devoirs d\'abord, les jeux ensuite !',
            'ad_text': 'Fournitures scolaires et bureaux enfants !',
            'ad_link': 'https://www.youtube.com/results?search_query=technique+pomodoro+enfant+devoirs'
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
            'ad_link': 'https://www.youtube.com/results?search_query=apprendre+enfant+ranger+jouets'
        },
        {
            'name': 'Lire 10 minutes par jour',
            'image': 'chambre enfant/lire dix minutes par jour.webp',
            'description': 'Un moment de lecture quotidien',
            'points': 3,
            'fun_text': '📚 Lire c\'est grandir !',
            'ad_text': 'Livres pour enfants !',
            'ad_link': 'https://www.youtube.com/results?search_query=lecture+enfant+habituer+livre'
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
            'ad_link': 'https://www.youtube.com/results?search_query=preparer+biberon+bebe+conseils'
        },
        {
            'name': 'Changer les couches',
            'image': 'chambre bébé/changer les couches.webp',
            'description': 'Un bébé propre et confortable !',
            'points': 4,
            'fun_text': '👶 Change moi vite !',
            'ad_text': 'Couches douces et absorbantes pour bébé !',
            'ad_link': 'https://www.youtube.com/results?search_query=changer+couche+bebe+technique'
        },
        {
            'name': 'Faire dormir le bébé',
            'image': 'chambre bébé/endormir le bébé.webp',
            'description': 'Un dodo paisible pour bébé !',
            'points': 6,
            'fun_text': '😴 Dodo, l\'enfant do !',
            'ad_text': 'Veilleuses et musiques douces pour endormir bébé !',
            'ad_link': 'https://www.youtube.com/results?search_query=endormir+bebe+technique+sommeil'
        },
        {
            'name': 'Laver les vêtements',
            'image': 'chambre bébé/laver les vêtements.webp',
            'description': 'Des petits habits tout propres !',
            'points': 4,
            'fun_text': '👕 Lessive spéciale bébé !',
            'ad_text': 'Lessives hypoallergéniques pour la peau de bébé !',
            'ad_link': 'https://www.youtube.com/results?search_query=laver+vetements+bebe+conseils'
        },
        {
            'name': 'Vider la poubelle',
            'image': 'chambre bébé/vider la poubelle.webp',
            'description': 'Vider la poubelle à couches !',
            'points': 3,
            'fun_text': '🗑️ Une chambre sans odeurs !',
            'ad_text': 'Poubelles à couches anti-odeurs !',
            'ad_link': 'https://www.youtube.com/results?search_query=couches+bebe+lavables+ecologique'
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
            'ad_link': 'https://www.youtube.com/results?search_query=nettoyer+toilettes+vinaigre+naturel'
        },
        {
            'name': 'Changer le rouleau de papier toilette',
            'image': 'wc/jeter_rouleaux.png',
            'description': '🧻 Tu peux jeter les rouleaux ou en faire des ronds de serviettes ! 😄',
            'points': 2,
            'fun_text': '🧻 Le héros silencieux de la maison !',
            'ad_text': 'Le saviez-vous ? Le papier recyclé est tout aussi doux et préserve 70% d\'eau à la fabrication.',
            'ad_link': 'https://www.youtube.com/results?search_query=papier+toilette+ecologique+choisir'
        },
        {
            'name': 'Relever la cuvette',
            'image': 'wc/relever la cuvette.Webp',
            'description': '🎯 Relève la lunette des toilettes… Bien viser ; essaye un peu pour voir ! 😉',
            'points': 1,
            'fun_text': '🚽 Un petit geste, un grand respect !',
            'ad_text': 'Astuce : un abattant WC à fermeture ralentie évite les claquements !',
            'ad_link': 'https://www.youtube.com/results?search_query=installer+abattant+wc+frein+chute'
        },
        {
            'name': 'Séjourner aux toilettes',
            'image': 'wc/séjourner aux toilettes.webp',
            'description': '📱 Eh oui, c\'est tentant de passer sa vie aux toilettes pour échapper aux corvées ! 😂',
            'points': -3,
            'fun_text': '📱 La bibliothèque préférée de la maison !',
            'ad_text': 'Un repose-pieds physiologique améliore le confort et la santé intestinale !',
            'ad_link': 'https://www.youtube.com/results?search_query=position+ideale+toilettes+sante'
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
            'ad_link': 'https://www.youtube.com/results?search_query=laver+voiture+technique+sans+rayures'
        },
        {
            'name': 'Prendre de l\'essence',
            'image': 'garage/Prendre de l\'essence.webp',
            'description': 'Faire le plein de carburant',
            'points': 3,
            'fun_text': '⛽ Le plein d\'énergie !',
            'ad_text': 'Carte carburant pour économiser !',
            'ad_link': 'https://www.youtube.com/results?search_query=eco+conduite+economiser+carburant'
        },
        {
            'name': 'Contrôle technique',
            'image': 'garage/contrôle technique .webp',
            'description': 'Passer le contrôle technique du véhicule',
            'points': 6,
            'fun_text': '🔧 Sécurité avant tout !',
            'ad_text': 'Kit d\'entretien auto !',
            'ad_link': 'https://www.youtube.com/results?search_query=entretien+voiture+conseils+mecanicien'
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
        c.execute("ALTER TABLE users ADD COLUMN bg_theme TEXT DEFAULT 'ocean'")
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
        c.execute("ALTER TABLE houses ADD COLUMN bg_theme TEXT DEFAULT 'bleu'")
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
            response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 heure (deploy fréquents)
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
        current = now_paris().date()
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


def create_system_message(house_id, content, message_type='system', related_task_id=None, send_push=True, sender_name=None, sender_email=None, related_category=None, push_title=None):
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
        """, (house_id, actual_sender if actual_sender and '@' in str(actual_sender) else None, content, message_type, related_task_id, related_category))
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
                
                # Titre personnalisé selon le type de notification
                notification_titles = {
                    'task_completed': '✅ CleanBeat',
                    'task_added': '⭐ Nouvelle mission !',
                    'courses_added': '🛒 Liste de courses',
                    'baby_tracking': '👶 Suivi bébé',
                }
                if push_title:
                    title = push_title
                elif message_type in ['sermon', 'congratulation', 'reminder']:
                    title = f'{icon_emoji} {sender_name or "Maison"}'
                elif message_type in notification_titles:
                    title = notification_titles[message_type]
                else:
                    title = f'{icon_emoji} CleanBeat'
                
                notification_data = {
                    'title': title,
                    'body': content,
                    'icon': '/static/images/logo.png',
                    'url': notif_url,
                    'messageId': message_id,
                    'messageType': message_type,
                    'badge': 1
                }
                
                # Exclure l'expéditeur du push pour baby_tracking, task_added et courses_added
                exclude = sender_email if message_type in ('baby_tracking', 'task_added', 'courses_added') else None
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
        if status_code in (404, 410, 401, 403):
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


def _get_house_courses_pending(house_id):
    """Compteur 'rappels courses non faits' partagé pour toute la maison."""
    try:
        _conn = get_db_connection()
        _c = _conn.cursor()
        _c.execute(
            "SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0",
            (house_id,)
        )
        n = _c.fetchone()[0] or 0
        _conn.close()
        return n
    except Exception:
        return 0


def compute_user_total_badge(user_email, house_id, courses_pending=None):
    """
    Total unifié des notifications non lues pour le badge PWA d'un utilisateur.
    Source unique de vérité — utilisée par notify_house_members() et routes/messages.add_comment().
    """
    if courses_pending is None:
        courses_pending = _get_house_courses_pending(house_id)
    try:
        return (
            get_unread_message_count(user_email, house_id) +
            get_unread_count_by_type(user_email, house_id, 'baby_tracking') +
            get_unread_count_by_type(user_email, house_id, 'task_added', include_own=True) +
            courses_pending
        )
    except Exception:
        return 0


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

    # courses_pending_count est identique pour tous les membres → 1 seule requête hors boucle
    _courses_pending = _get_house_courses_pending(house_id)

    success_count = 0
    for sub in subscriptions:
        user_email = sub.get('user_email')
        # Calculer le badge count réel pour cet utilisateur via le helper unifié
        personalized_data = dict(notification_data)
        if user_email:
            try:
                total = compute_user_total_badge(user_email, house_id, courses_pending=_courses_pending)
                personalized_data['badge'] = max(1, total)
            except Exception:
                personalized_data['badge'] = 1
        if send_push_notification(sub, personalized_data):
            success_count += 1
    
    print(f"🔔 notify_house_members: {success_count}/{len(subscriptions)} push envoyé(s)", flush=True)
    return success_count


# 🔔 ========== FIN FONCTIONS PUSH NOTIFICATIONS ==========




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
    today = now_paris().date().isoformat()
    
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

    # 🚀 BATCH: calculer weekly_points pour TOUS les joueurs en 1 seule requête (👑 couronne)
    from datetime import timedelta
    _today = now_paris().date()
    _week_start = (_today - timedelta(days=_today.weekday())).isoformat()
    _weekly_map = {}  # {email: points}
    try:
        c.execute("""
            SELECT user_email, COALESCE(SUM(points),0)
            FROM completed_tasks
            WHERE house_id=? AND DATE(completed_at) >= ?
            GROUP BY user_email
        """, (house_id, _week_start))
        for row_wp in c.fetchall():
            _weekly_map[row_wp[0]] = int(row_wp[1]) if row_wp[1] else 0
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
                skull_active = datetime.fromisoformat(str(skull_expires_at_raw)) > now_paris()
            except Exception:
                pass
        # Bonus actif (❤️)
        bonus_active = False
        if bonus_expires_at_raw:
            try:
                bonus_active = datetime.fromisoformat(str(bonus_expires_at_raw)) > now_paris()
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
        weekly_points = _weekly_map.get(email, 0)

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
            'weekly_points': weekly_points,
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

@app.route('/menu')
def menu():
    from datetime import datetime
    _dbg(f"🚨🚨🚨 ROUTE /menu APPELÉE à {now_paris()} 🚨🚨🚨")

    players = []
    current_user_name = session.get('user', '')
    house_name = None
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
                return redirect(url_for('auth.welcome'))
            
            show_onboarding = False  # Slides remplacées par les bulles QfqTips
            is_invited_player = bool(session.get('invite_code') or session.get('joined_via_invite'))
            onboarding_type = 'invited' if is_invited_player else 'creator'
            print(f"🏠 MENU CHECK: name={user_name}, avatar={user_avatar}, file={user_avatar_file}, step={registration_step}", flush=True)
            
            # Si le parcours d'inscription n'est pas terminé
            if registration_step not in ('profile_created', 'complete'):
                conn.close()
                flash("Complète ton profil pour commencer à jouer ! 🎭", "info")
                return redirect(url_for('players.create_profile'))
            
            if not user_name:
                conn.close()
                flash("Complète ton profil pour commencer à jouer ! 🎭", "info")
                return redirect(url_for('players.create_profile'))
            
            # Si l'utilisateur n'a pas de maison, rediriger vers la page d'invitation
            if not house_id:
                conn.close()
                flash("Crée ou rejoins une maison pour commencer à jouer ! 🏠", "info")
                return redirect(url_for('house.invite_partner'))
            
            # Réinitialisation quotidienne de la santé/progression de la maison
            try:
                today = now_paris().date().isoformat()
                c.execute("SELECT health, last_reset_date FROM houses WHERE id=?", (house_id,))
                hrow = c.fetchone()
                if hrow:
                    current_last_reset = hrow[1]
                    if current_last_reset != today:
                        c.execute("UPDATE houses SET health=?, last_reset_date=? WHERE id=?", (0, today, house_id))
                        conn.commit()
            except Exception:
                try:
                    today = now_paris().date().isoformat()
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
            unread_baby_tracking = get_unread_count_by_type(session['user'], house_id, 'baby_tracking', existing_conn=conn, include_own=False)
            unread_task_added = get_unread_count_by_type(session['user'], house_id, 'task_added', existing_conn=conn, include_own=True)
            _dbg(f"🔔 DEBUG menu - {session['user']}: unread_messages_count={unread_messages_count}, baby={unread_baby_tracking}, task_added={unread_task_added}, children_unread={children_unread}")

            # 🛒 Articles non cochés dans la liste de courses (badge onglet navigation)
            courses_pending_count = _get_house_courses_pending(house_id)

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
                            AND ctd.task_name = ct.task_name
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
        {'key': 'chambre_parentale', 'name': 'Chambre 1',    'image': 'images/thumbs/chambreparentale_marron.webp', 'category': 'chambre_parentale', 'fixed': False},
        {'key': 'chambre1',          'name': 'Chambre 2',    'image': 'images/thumbs/chambre1.webp',                'category': 'chambre_parentale',  'fixed': False},
        {'key': 'chambre2',          'name': 'Chambre 3',    'image': 'images/thumbs/chambre2.webp',                'category': 'chambre_parentale',  'fixed': False},
        {'key': 'chambre_garcon',    'name': 'Chambre 4',    'image': 'images/thumbs/chambre_garçon3.webp',        'category': 'chambre_garcon',     'fixed': False},
        {'key': 'chambre_enfant',    'name': 'Chambre 5',    'image': 'images/thumbs/chambre_enfant_4.webp',       'category': 'chambre_enfant',     'fixed': False},
        {'key': 'chambre_bebe',      'name': 'Chambre bébé', 'image': 'images/thumbs/chambre_bébé4_.webp',         'category': 'chambre_bebe',       'fixed': False},
        # Pièces fixes (ne peuvent pas être masquées, mais renommables)
        {'key': 'cuisine',  'name': 'Cuisine',      'image': 'images/thumbs/cuisinewoop.webp',  'category': 'cuisine',    'fixed': True},
        {'key': 'salon',    'name': 'Salon',        'image': 'images/thumbs/salonorange.webp',  'category': 'salon',      'fixed': True},
        {'key': 'bureau',   'name': 'Bureau',       'image': 'images/thumbs/bureau.webp',       'category': 'piece_bonus', 'fixed': True},
        {'key': 'salle_bain','name': 'Salle de bain','image': 'images/thumbs/sdbwoop.webp',     'category': 'salle_bain', 'fixed': True},
        {'key': 'toilettes','name': 'Toilettes',    'image': 'images/thumbs/Wc2.webp',          'category': 'wc',         'fixed': True},
        {'key': 'buanderie','name': 'Buanderie',    'image': 'images/thumbs/buanderie5.webp',   'category': 'buanderie',  'fixed': True},
        {'key': 'garage',   'name': 'Garage',       'image': 'images/thumbs/Garage2.webp',      'category': 'garage',     'fixed': False},
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

    # 👑 Déterminer le leader du jour (halo+pulse) et le gagnant hebdomadaire (couronne dimanche)
    _now = now_paris()
    _is_sunday = (_now.weekday() == 6)
    # ⚙️ DEV: forcer dimanche via ?preview_sunday=1 (pour accès cadeaux)
    if request.args.get('preview_sunday') == '1':
        _is_sunday = True

    # Leader du jour = celui avec le plus de daily_points
    _daily_leader_email = ''
    if players:
        _sorted_daily = sorted(players, key=lambda x: x.get('daily_points', 0), reverse=True)
        if _sorted_daily and _sorted_daily[0].get('daily_points', 0) > 0:
            _daily_leader_email = _sorted_daily[0].get('email', '')

    # Gagnant de la semaine = celui avec le plus de weekly_points (couronne dimanche uniquement)
    _winner_name = ''
    _winner_email = ''
    _has_weekly_winner = False
    if _is_sunday and players:
        _sorted_weekly = sorted(players, key=lambda x: x.get('weekly_points', 0), reverse=True)
        if _sorted_weekly and _sorted_weekly[0].get('weekly_points', 0) > 0:
            _winner_name = _sorted_weekly[0].get('name', '')
            _winner_email = _sorted_weekly[0].get('email', '')
            _has_weekly_winner = True

    # ⏰ Rappel quotidien — popup déclenché UNIQUEMENT via WebSocket à 20h ou clic notif push
    # (Pas de check au chargement → évite affichage non sollicité)
    show_daily_reminder = False
    daily_reminder_message = None
    daily_reminder_message_id = None

    resp = make_response(render_template(
        'menu.html',
        players=players,
        current_user_name=current_user_name,
        current_user_daily_points=next((p.get('daily_points',0) for p in players if p.get('email')==current_user_name), 0),
        is_child_account=is_child_account if 'is_child_account' in locals() else 0,  # Statut enfant de l'utilisateur actuel
        menu_page=True,
        house_name=house_name,
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
        onboarding_type=onboarding_type if 'onboarding_type' in dir() else 'creator',
        is_invited_player=is_invited_player if 'is_invited_player' in dir() else False,
        rooms_with_new_missions=rooms_with_new_missions,
        is_sunday=_is_sunday,
        has_weekly_winner=_has_weekly_winner,
        winner_name=_winner_name,
        winner_email=_winner_email,
        daily_leader_email=_daily_leader_email,
        show_daily_reminder=show_daily_reminder,
        daily_reminder_message=daily_reminder_message,
        daily_reminder_message_id=daily_reminder_message_id,
    ))
    # Désactiver le cache pour éviter d'afficher d'anciennes valeurs de daily_points
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/api/mark_reminder_read', methods=['POST'])
def mark_reminder_read():
    """Marquer un message reminder comme lu (appelé au clic sur 'Je vais valider')"""
    if 'user' not in session:
        return jsonify({'error': 'not logged in'}), 401
    data = request.get_json(silent=True) or {}
    message_id = data.get('message_id')
    if not message_id:
        return jsonify({'error': 'missing message_id'}), 400
    user_email = session['user']
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'INSERT INTO message_reads (message_id, user_email) VALUES (?, ?) ON CONFLICT(message_id, user_email) DO NOTHING',
            (message_id, user_email)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        _dbg(f'❌ Erreur mark_reminder_read: {e}')
        return jsonify({'error': 'db error'}), 500
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════
# 👤 PAGE PROFIL — Page complète du profil joueur
# ════════════════════════════════════════════════════════════
@app.route('/ping')
def ping():
    return 'OK', 200, {'Content-Type': 'text/plain; charset=utf-8'}

# 🚀 Page promo / invitation beta testeurs (partageable SMS / WhatsApp / mail)
@app.route('/beta')
def beta_invite():
    return render_template('beta_invite.html')

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
    today = now_paris().date().isoformat()
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
        children_unread = get_children_unread_counts(house_id)
        unread_baby = get_unread_count_by_type(session['user'], house_id, 'baby_tracking', include_own=False)
        unread_task_added = get_unread_count_by_type(session['user'], house_id, 'task_added', include_own=True)
        unread_courses_added = get_unread_count_by_type(session['user'], house_id, 'courses_added', include_own=True)

        # 🛒 Articles non cochés dans la liste de courses
        courses_pending_count = _get_house_courses_pending(house_id)
        
        conn.close()
        
        resp = jsonify({
            'unread_received': unread_received,
            'unread_by_sender': {},
            'unread_sent_to': {},
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

    @socketio.on('typing')
    def handle_typing(data):
        """Diffuser l'indicateur de frappe à tous les membres de la maison"""
        try:
            user_email = data.get('user_email')
            user_name = data.get('user_name')
            if not user_email or not user_name:
                return
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT house_id FROM users WHERE email=?', (user_email,))
            row = c.fetchone()
            conn.close()
            if row and row[0]:
                house_id = row[0]
                safe_socketio_emit('user_typing', {
                    'user_name': user_name,
                    'user_email': user_email
                }, namespace='/', room=f'house_{house_id}', broadcast=True)
        except Exception as e:
            _dbg(f'❌ Erreur handle_typing: {e}')

    @socketio.on('stop_typing')
    def handle_stop_typing(data):
        """Diffuser l'arrêt de frappe à tous les membres de la maison"""
        try:
            user_email = data.get('user_email')
            if not user_email:
                return
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT house_id FROM users WHERE email=?', (user_email,))
            row = c.fetchone()
            conn.close()
            if row and row[0]:
                house_id = row[0]
                safe_socketio_emit('user_stop_typing', {
                    'user_email': user_email
                }, namespace='/', room=f'house_{house_id}', broadcast=True)
        except Exception as e:
            _dbg(f'❌ Erreur handle_stop_typing: {e}')


# 🏠 ========== ROUTES TEST MESSAGES MAISON ==========
# ─── KEEP-ALIVE supprimé (plan payant Render → serveur toujours allumé) ──────


# ─── BLUEPRINTS ──────
from routes.rewards import rewards_bp
app.register_blueprint(rewards_bp)

from routes.messages import messages_bp
app.register_blueprint(messages_bp)

from routes.stats import stats_bp
app.register_blueprint(stats_bp)

from routes.gameplay import gameplay_bp
app.register_blueprint(gameplay_bp)

from routes.players import players_bp
app.register_blueprint(players_bp)

from routes.tasks import tasks_bp
app.register_blueprint(tasks_bp)

from routes.reminders import reminders_bp
app.register_blueprint(reminders_bp)

from routes.baby import baby_bp
app.register_blueprint(baby_bp)

from routes.auth import auth_bp
app.register_blueprint(auth_bp)

from routes.admin import admin_bp
app.register_blueprint(admin_bp)

from routes.house import house_bp
app.register_blueprint(house_bp)

from routes.customize import customize_bp
app.register_blueprint(customize_bp)

from routes.suspicion import suspicion_bp
app.register_blueprint(suspicion_bp)

from routes.push import push_bp
app.register_blueprint(push_bp)

# 🏠 ========== BOUCLE AUTOMATIQUE RAPPEL QUOTIDIEN / DAILY REMINDER ==========
def _daily_reminder_loop():
    while True:
        try:
            # Calcule le temps jusqu'à 20h heure Paris
            now = now_paris()
            target = now.replace(hour=20, minute=0, second=0, microsecond=0)
            if now >= target:
                target = target + timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            socketio.sleep(wait_seconds)

            # Envoie le rappel à tous les joueurs inactifs de toutes les maisons
            conn = get_db_connection()
            c = conn.cursor()

            # Récupère tous les joueurs sans validation aujourd'hui
            paris_today = now_paris().strftime('%Y-%m-%d')
            c.execute("""
                SELECT u.email, u.name, u.house_id
                FROM users u
                WHERE u.house_id IS NOT NULL
                AND u.is_child_account = 0
                AND EXISTS (SELECT 1 FROM houses h WHERE h.id = u.house_id)
                AND NOT EXISTS (
                    SELECT 1 FROM completed_tasks ct
                    WHERE ct.user_email = u.email
                    AND ct.completed_at::date = ?
                )
                AND EXISTS (
                    SELECT 1 FROM completed_tasks ct2
                    WHERE ct2.user_email = u.email
                    AND ct2.completed_at >= CURRENT_DATE - INTERVAL '30 days'
                )
            """, (paris_today,))
            inactive_players = c.fetchall()
            conn.close()

            message = (
                "Rien de validé aujourd'hui... "
                "mais attends — t'as bien fait "
                "quelque chose non ? T'as mis de "
                "l'essence ? Fait un café ? Lancé "
                "une machine ? Brossé tes dents ?\n\n"
                "Chaque petit geste compte ! Valide "
                "tes tâches et rappelle-toi — chaque "
                "effort mérite sa récompense 🏆"
            )

            houses_done = set()
            for player in inactive_players:
                player_email = player[0]
                house_id = player[2]

                # Notification push (individuel par joueur)
                try:
                    subs = get_house_push_subscriptions(
                        house_id,
                        exclude_email=None
                    )
                    player_subs = [
                        s for s in subs
                        if s.get('user_email') == player_email
                    ]
                    for sub in player_subs:
                        send_push_notification(sub, {
                            'title': "Hé, t'es là ? 👀",
                            'body': "Rien de validé aujourd'hui... chaque petit geste compte !",
                            'url': '/menu',
                            'icon': '/static/images/logo.png'
                        })
                except Exception:
                    pass

                # Message in-app → une seule fois par maison
                if house_id not in houses_done:
                    houses_done.add(house_id)
                    try:
                        create_system_message(
                            house_id,
                            message,
                            'reminder',
                            sender_email=None,
                            send_push=False
                        )
                    except Exception:
                        pass

                # Toast temps réel via WebSocket
                try:
                    safe_socketio_emit('daily_reminder', {
                        'message': message
                    }, namespace='/', room=f'house_{house_id}', broadcast=True)
                except Exception:
                    pass

        except Exception as e:
            _dbg(f"❌ Erreur daily_reminder_loop: {e}")
            socketio.sleep(3600)

if SOCKETIO_AVAILABLE and socketio:
    socketio.start_background_task(_daily_reminder_loop)
    _dbg("🏠 Background task daily_reminder enregistrée")
# 🏠 ========== FIN BOUCLE RAPPEL QUOTIDIEN / DAILY REMINDER ==========

# 🔐 ========== CRON ENDPOINT EXTERNE / DAILY REMINDER ==========
@app.route('/api/cron/daily-reminder', methods=['POST'])
def cron_daily_reminder():
    token = request.headers.get('X-Cron-Secret', '')
    if token != os.environ.get('CRON_SECRET', ''):
        return jsonify({'error': 'unauthorized'}), 401

    try:
        paris_today = now_paris().strftime('%Y-%m-%d')
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT u.email, u.name, u.house_id
            FROM users u
            WHERE u.house_id IS NOT NULL
            AND u.is_child_account = 0
            AND EXISTS (SELECT 1 FROM houses h WHERE h.id = u.house_id)
            AND NOT EXISTS (
                SELECT 1 FROM completed_tasks ct
                WHERE ct.user_email = u.email
                AND ct.completed_at::date = ?
            )
            AND EXISTS (
                SELECT 1 FROM completed_tasks ct2
                WHERE ct2.user_email = u.email
                AND ct2.completed_at >= CURRENT_DATE - INTERVAL '30 days'
            )
        """, (paris_today,))
        inactive_players = c.fetchall()
        conn.close()

        print(f"⏰ CRON 20h: {len(inactive_players)} joueurs inactifs", flush=True)

        message = (
            "Rien de validé aujourd'hui... "
            "mais attends — t'as bien fait "
            "quelque chose non ? T'as mis de "
            "l'essence ? Fait un café ? Lancé "
            "une machine ? Brossé tes dents ?\n\n"
            "Chaque petit geste compte ! Valide "
            "tes tâches et rappelle-toi — chaque "
            "effort mérite sa récompense 🏆"
        )

        houses_done = set()
        details = []
        for player in inactive_players:
            player_email = player[0]
            player_name = player[1]
            house_id = player[2]
            push_sent = 0
            push_failed = 0
            push_error = None
            subs_count = 0

            try:
                subs = get_house_push_subscriptions(house_id, exclude_email=None)
                player_subs = [s for s in subs if s.get('user_email') == player_email]
                subs_count = len(player_subs)
                for sub in player_subs:
                    try:
                        # ✅ Inclure 'badge': 1 → setAppBadge sur l'icône d'accueil
                        # ⚠️ Utiliser le RETOUR (True/False), send_push_notification ne lève pas
                        ok = send_push_notification(sub, {
                            'title': "Hé, t'es là ? 👀",
                            'body': "Rien de validé aujourd'hui... chaque petit geste compte !",
                            'url': '/menu',
                            'icon': '/static/images/logo.png',
                            'badge': 1,
                            'tag': f'reminder-{paris_today}',
                            'requireInteraction': True
                        })
                        if ok:
                            push_sent += 1
                        else:
                            push_failed += 1
                            if not push_error:
                                push_error = 'send_push_notification returned False (sub probablement expirée)'
                    except Exception as pe:
                        push_failed += 1
                        push_error = str(pe)[:200]
            except Exception as e:
                push_error = str(e)[:200]
                print(f"❌ Push error: {e}", flush=True)

            details.append({
                'name': player_name,
                'email': player_email,
                'house_id': house_id,
                'subs_count': subs_count,
                'push_sent': push_sent,
                'push_failed': push_failed,
                'push_error': push_error
            })

            if house_id not in houses_done:
                houses_done.add(house_id)
                try:
                    create_system_message(
                        house_id, message, 'reminder',
                        sender_email=None, send_push=False)
                except Exception as e:
                    print(f"❌ Message error: {e}", flush=True)

        # Émet le popup en temps réel pour les joueurs connectés
        houses_ws = set()
        for player in inactive_players:
            house_id = player[2]
            if house_id not in houses_ws:
                houses_ws.add(house_id)
                try:
                    safe_socketio_emit('daily_reminder', {
                        'message': message
                    }, namespace='/', room=f'house_{house_id}', broadcast=True)
                except Exception:
                    pass

        return jsonify({'success': True, 'players_notified': len(inactive_players), 'details': details})

    except Exception as e:
        print(f"❌ CRON error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
# 🔐 ========== FIN CRON ENDPOINT ==========

@app.route('/api/cron/list-players', methods=['GET'])
def cron_list_players():
    token = request.headers.get('X-Cron-Secret', '')
    if token != os.environ.get('CRON_SECRET', ''):
        return jsonify({'error': 'unauthorized'}), 401
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT u.name, u.email, u.house_id, u.points,
                   MAX(ct.completed_at) as last_task
            FROM users u
            LEFT JOIN completed_tasks ct ON ct.user_email = u.email
            WHERE u.house_id IS NOT NULL
            AND u.is_child_account = 0
            GROUP BY u.id, u.name, u.email, u.house_id, u.points
            ORDER BY last_task DESC NULLS LAST
        """)
        rows = c.fetchall()
        conn.close()
        players = [
            {'name': r[0], 'email': r[1], 'house_id': r[2],
             'points': r[3], 'last_task': str(r[4]) if r[4] else None}
            for r in rows
        ]
        return jsonify({'success': True, 'count': len(players), 'players': players})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



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