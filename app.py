from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, send_file, jsonify, make_response
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
import time
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

        conn = sqlite3.connect(DB)
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
app.secret_key = "2b7e4f8c-9a1d-4e2a-8c3e-7f5d1a2b9c4e-2025"  # clé secrète forte, à garder confidentielle

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
app.config['SESSION_COOKIE_SECURE'] = False  # Mettre à True en production avec HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialiser SocketIO si disponible
if SOCKETIO_AVAILABLE:
    # Configurer SocketIO avec les bons paramètres pour WebSocket
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        logger=False,  # Désactiver les logs verbeux
        engineio_logger=False,  # Désactiver les logs engine.io
        ping_timeout=60,  # Timeout plus long pour la stabilité
        ping_interval=25,  # Ping régulier pour maintenir la connexion
        async_mode=None  # Laisser SocketIO choisir le meilleur mode (eventlet si disponible, sinon threading)
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
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
            row = c.fetchone()
            if row and row[0]:
                house_id = row[0]
                # Essayer de récupérer un nom simple et un code de maison si la table existe
                try:
                    c.execute("SELECT house_name, code FROM houses WHERE id=?", (house_id,))
                    hr = c.fetchone()
                    if hr:
                        house_name = hr[0] if hr[0] and hr[0].strip() else None
                        house_code = hr[1] if len(hr) > 1 else None
                except sqlite3.OperationalError:
                    # Ancienne base sans table/colonnes 'houses' -> on ignore
                    pass
            conn.close()
    except Exception:
        pass
    # Fournir aussi un booléen pour savoir si on est sur la page menu
    return {
        'global_house_name': house_name,
        'global_house_code': house_code,
    }

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
            'pièce bonus': 'la pièce bonus',
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
    
    conn = sqlite3.connect(DB)
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
        
        # === RÉCUPÉRER LES JOUEURS DE LA MAISON ===
        c.execute("""
            SELECT email, name, avatar, avatar_url, avatar_file, points 
            FROM users WHERE house_id=?
        """, (house_id,))
        users_rows = c.fetchall()
        
        players = []
        for u in users_rows:
            email, name, avatar_emoji, avatar_url, avatar_file, total_points = u
            
            # Résoudre l'avatar : priorité avatar_file > avatar_url > avatar (fichier PNG) > avatar emoji > défaut
            resolved_avatar_file = None
            resolved_avatar_url = None
            resolved_avatar_emoji = None
            
            # 1. Si avatar_file est défini, l'utiliser
            if avatar_file and avatar_file != 'None':
                resolved_avatar_file = avatar_file
            # 2. Si avatar_url est défini
            elif avatar_url and avatar_url != 'None':
                resolved_avatar_url = avatar_url
            # 3. Sinon analyser le champ avatar
            elif avatar_emoji:
                avatar_str = str(avatar_emoji).strip()
                
                # Est-ce un fichier image (.png, .jpg, .jpeg) ?
                if any(avatar_str.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    resolved_avatar_file = avatar_str
                # Est-ce un emoji ? (caractères Unicode > 127, max 4 chars)
                elif (len(avatar_str) <= 4 and 
                      any(ord(c) > 127 for c in avatar_str) and
                      'http' not in avatar_str.lower() and
                      '/' not in avatar_str):
                    resolved_avatar_emoji = avatar_str
                # Sinon c'est probablement un index numérique ou autre -> défaut
            
            # Points du jour
            c.execute("""
                SELECT COALESCE(SUM(points), 0), COUNT(*) 
                FROM completed_tasks 
                WHERE user_email=? AND DATE(completed_at, 'localtime')=?
            """, (email, today))
            daily = c.fetchone()
            daily_points = int(daily[0]) if daily[0] else 0
            daily_tasks = int(daily[1]) if daily[1] else 0
            
            # Points de la semaine (depuis lundi)
            week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
            c.execute("""
                SELECT COALESCE(SUM(points), 0), COUNT(*) 
                FROM completed_tasks 
                WHERE user_email=? AND DATE(completed_at, 'localtime') >= ?
            """, (email, week_start))
            weekly = c.fetchone()
            weekly_points = int(weekly[0]) if weekly[0] else 0
            weekly_tasks = int(weekly[1]) if weekly[1] else 0
            
            # Détails des tâches de la semaine pour ce joueur
            c.execute("""
                SELECT task_name, points, category
                FROM completed_tasks 
                WHERE user_email=? AND DATE(completed_at, 'localtime') >= ?
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
            
            players.append({
                'email': email,
                'name': name if name else email.split('@')[0],
                'avatar': resolved_avatar_emoji,  # Emoji direct si valide
                'avatar_url': resolved_avatar_url,  # URL si présente
                'avatar_file': resolved_avatar_file,  # Fichier (uploadé ou PNG prédéfini)
                'total_points': total_points if total_points else 0,
                'daily_points': daily_points,
                'daily_tasks': daily_tasks,
                'weekly_points': weekly_points,
                'weekly_tasks': weekly_tasks,
                'weekly_tasks_details': weekly_tasks_details,
                'is_current_user': (email == session['user'])
            })
        
        # Trier par points de la semaine (pour le classement général et le leader)
        # Le template fera le tri par daily_points pour le podium du jour
        players.sort(key=lambda x: x['weekly_points'], reverse=True)
        
        # Attribuer les rangs
        for idx, p in enumerate(players, start=1):
            p['rank'] = idx
        
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
              AND DATE(ct.completed_at, 'localtime') = ?
            ORDER BY ct.completed_at DESC
        """, (house_id, today))
        
        tasks_rows = c.fetchall()
        tasks_history = []
        
        for t in tasks_rows:
            email, task_name, points, completed_at, category, name, avatar_url, avatar_file = t
            
            # Résoudre l'avatar
            if avatar_file:
                avatar = url_for('static', filename=f'avatars/{avatar_file}')
            elif avatar_url:
                avatar = avatar_url
            else:
                avatar = url_for('static', filename='avatars/homme.png')
            
            # Extraire l'heure
            try:
                dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M')
            except:
                time_str = completed_at.split(' ')[1][:5] if ' ' in completed_at else '??:??'
            
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
              AND DATE(completed_at, 'localtime') = ?
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
            'chambre_parentale': ('Chambre Parentale', '🛏️'),
            'salle_bain': ('Salle de bain', '🛁'),
            'salle_de_bain': ('Salle de bain', '🛁'),
            'chambre_enfant': ('Chambre Enfant', '🧸'),
            'chambre_bebe': ('Chambre Bébé', '👶'),
            'chambre_ado': ('Zone Ados', '🎮'),
            'piece_bonus': ('Pièce Bonus', '💎'),
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
              AND DATE(ct.completed_at, 'localtime') = ?
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
                room_image = ROOM_IMAGES.get(category, 'images/newmaison.png')
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
              AND DATE(completed_at, 'localtime') >= ?
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
        print(f"\n{'='*60}")
        print(f"❌ ERREUR PAGE STATS (/sats)")
        print(f"{'='*60}")
        print(f"Exception: {e}")
        print(f"Type: {type(e).__name__}")
        print(f"\nTraceback complet:")
        print(error_details)
        print(f"{'='*60}\n")
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
    
    conn = sqlite3.connect(DB)
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
                WHERE user_email=? AND DATE(completed_at, 'localtime')=?
            """, (session['user'], day.isoformat()))
            points = c.fetchone()[0]
            daily_points_values.append(int(points) if points else 0)
        
        # === DONNÉES POUR GRAPHIQUE 2: Comparaison joueurs ===
        c.execute("""
            SELECT u.name, u.email, COALESCE(SUM(ct.points), 0) as total_points
            FROM users u
            LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                AND DATE(ct.completed_at, 'localtime') >= ?
            WHERE u.house_id = ?
            GROUP BY u.email
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
            WHERE house_id = ? AND DATE(completed_at, 'localtime') >= ?
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
                AND CAST(strftime('%w', DATE(completed_at, 'localtime')) AS INTEGER) = ?
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
            WHERE user_email=? AND DATE(completed_at, 'localtime') >= ?
        """, (session['user'], week_start))
        total_weekly_points = int(c.fetchone()[0] or 0)
        
        # Tâches totales de la semaine
        c.execute("""
            SELECT COUNT(*)
            FROM completed_tasks
            WHERE user_email=? AND DATE(completed_at, 'localtime') >= ?
        """, (session['user'], week_start))
        total_weekly_tasks = int(c.fetchone()[0] or 0)
        
        # Moyenne par jour
        avg_daily_points = round(total_weekly_points / 7, 1) if total_weekly_points > 0 else 0
        
        # Classement
        c.execute("""
            SELECT u.email, COALESCE(SUM(ct.points), 0) as total_points
            FROM users u
            LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                AND DATE(ct.completed_at, 'localtime') >= ?
            WHERE u.house_id = ?
            GROUP BY u.email
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
        print(f"Erreur page stats graphique: {e}")
        print(traceback.format_exc())
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

DB = "users.db"

# Migration idempotente au démarrage: s'assurer que la colonne `avatar_style` existe
try:
    conn_m = sqlite3.connect(DB)
    c_m = conn_m.cursor()
    c_m.execute("PRAGMA table_info(users)")
    cols_m = [r[1] for r in c_m.fetchall()]
    if 'avatar_style' not in cols_m:
        try:
            c_m.execute("ALTER TABLE users ADD COLUMN avatar_style TEXT")
            conn_m.commit()
            print("✅ Migration: colonne 'avatar_style' ajoutée à users")
        except Exception as e:
            print(f"⚠️ Migration avatar_style échouée: {e}")
    conn_m.close()
except Exception:
    pass

# Nombre maximum de joueurs par maison. Mettre à `None` pour illimité.
MAX_PLAYERS = None

# ===============================
# CONNEXION SQLITE OPTIMISÉE
# ===============================

def get_db_connection(timeout=30.0):
    """
    Crée une connexion SQLite avec timeout et configuration optimisée
    pour éviter les blocages en production
    """
    conn = sqlite3.connect(DB, timeout=timeout, check_same_thread=False)
    # Activer le mode WAL pour permettre lectures/écritures concurrentes
    conn.execute('PRAGMA journal_mode=WAL')
    # Optimisations de performance
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=10000')
    conn.execute('PRAGMA temp_store=MEMORY')
    return conn

# ===============================
# FONCTIONS UTILITAIRES
# ===============================

def allowed_file(filename):
    """Vérifie si le fichier est autorisé"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_photo_from_base64(base64_data):
    """Sauvegarde une photo à partir de données base64"""
    try:
        # Décoder le base64
        header, data = base64_data.split(',', 1)
        image_data = base64.b64decode(data)
        
        # Générer un nom de fichier unique
        filename = str(uuid.uuid4()) + '.jpg'
        
        # Assurer que le dossier existe
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Sauvegarder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        return filename
    except Exception as e:
        print(f"Erreur sauvegarde photo: {e}")
        return None

def get_avatar_url(avatar_id):
    """Retourne l'URL de l'avatar basé sur l'ID avec DiceBear Lorelei"""
    seeds = [
        'default', 'alice', 'bella', 'chloe', 'diana', 'emma',
        'fiona', 'grace', 'hannah', 'iris', 'julia', 'kate'
    ]
    
    try:
        seed = seeds[int(avatar_id)]
    except (ValueError, IndexError):
        seed = seeds[0]
    
    return f'https://api.dicebear.com/7.x/lorelei/svg?seed={seed}'

def send_sms_invitation(phone_number, user_name, house_code=None):
    """Envoie un SMS d'invitation"""
    if not TWILIO_AVAILABLE:
        if house_code:
            print(f"\n📱 SMS simulé envoyé vers {phone_number}:")
            print(f"   🏠 {user_name} vous invite à jouer à CleanBeat !")
            print(f"   📱 Cliquez pour rejoindre (aucune installation requise) :")
            print(f"   http://192.168.1.156:8000/join_house?code={house_code}")
            print(f"   Code : {house_code}\n")
        else:
            print(f"SMS simulé vers {phone_number}: {user_name} vous invite à jouer à CleanBeat !")
            print(f"📱 Cliquez : http://192.168.1.156:8000")
        return True
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        if house_code:
            message_body = f"🏠 {user_name} vous invite à jouer à 'CleanBeat' ! " \
                          f"📱 Cliquez pour rejoindre (aucune installation requise) : " \
                          f"http://192.168.1.156:8000/join_house?code={house_code} " \
                          f"Code : {house_code}"
        else:
            message_body = f"🏠 {user_name} vous invite à jouer à 'CleanBeat' ! " \
                          f"📱 Cliquez pour commencer : http://192.168.1.156:8000"
        
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        print(f"SMS envoyé avec succès: {message.sid}")
        return True
        
    except Exception as e:
        print(f"Erreur envoi SMS: {e}")
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
            'image': 'chambre bébé/Donner le biberon.webp',
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
            'name': 'Laver les biberons',
            'image': 'chambre bébé/laver les biberons.webp',
            'description': 'Des biberons propres et stérilisés !',
            'points': 3,
            'fun_text': '🧼 Propreté = santé !',
            'ad_text': 'Stérilisateurs et goupillons pour biberons !',
            'ad_link': 'https://www.amazon.fr/s?k=sterilisateur+biberon'
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
        'Pièce Bonus': 'piece_bonus',
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
        'chambre parentale': 'chambre_parentale',
        'chambre_parentale': 'chambre_parentale',
        'salle bain': 'salle_bain',
        'salle_bain': 'salle_bain',
        'chambre enfant': 'chambre_enfant',
        'chambre_enfant': 'chambre_enfant',
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
    conn = sqlite3.connect(DB)
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
    '#FF6B9D',  # Rose vif
    '#4ECDC4',  # Turquoise
    '#FFD93D',  # Jaune doré
    '#95E1D3',  # Menthe
    '#C7CEEA',  # Lavande
    '#FFA07A',  # Saumon
    '#98D8C8',  # Vert d'eau
    '#F7B7A3',  # Pêche
    '#A8DADC',  # Bleu ciel
    '#FFB6B9',  # Rose poudré
    '#B4A7D6',  # Violet pastel
    '#FFE66D',  # Jaune pastel
]


def assign_player_color(email, house_id=None):
    """
    Attribue une couleur unique à un joueur dans sa maison.
    Si house_id est fourni, s'assure que la couleur est unique dans la maison.
    Sinon, assigne une couleur aléatoire.
    """
    conn = sqlite3.connect(DB)
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
    conn = sqlite3.connect(DB)
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
    conn = sqlite3.connect(DB)
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
                'avatar_file': avatar_file,
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
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    points INTEGER DEFAULT 0,
    house_id INTEGER,
    avatar TEXT DEFAULT 'default.png',
    name TEXT,
    photo_filename TEXT,
    avatar_url TEXT,
    FOREIGN KEY(house_id) REFERENCES houses(id)
)
""")

    # Ajouter les nouvelles colonnes users si elles n'existent pas
    try:
        c.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN photo_filename TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
    except sqlite3.OperationalError:
        pass

    # Colonnes pour les comptes enfants
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_child_account INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN created_by TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Colonne pour la couleur personnelle du joueur
    try:
        c.execute("ALTER TABLE users ADD COLUMN player_color TEXT")
    except sqlite3.OperationalError:
        pass

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
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE houses ADD COLUMN progress INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Colonnes ajoutées dans des versions ultérieures
    try:
        c.execute("ALTER TABLE houses ADD COLUMN health INTEGER DEFAULT 100")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE houses ADD COLUMN level INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE houses ADD COLUMN mood TEXT DEFAULT 'happy'")
    except sqlite3.OperationalError:
        pass
    # Réinitialisation quotidienne: stocker la dernière date de reset
    try:
        c.execute("ALTER TABLE houses ADD COLUMN last_reset_date TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Type de foyer pour les récompenses (family, couple, coloc)
    try:
        c.execute("ALTER TABLE houses ADD COLUMN house_type TEXT DEFAULT 'family'")
    except sqlite3.OperationalError:
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
    except sqlite3.OperationalError:
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
    except sqlite3.OperationalError:
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

    # Table pour les cadeaux révélés (CleanBeat)
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

    # === INDEX POUR AMÉLIORER LES PERFORMANCES ===
    # Index sur completed_tasks pour les requêtes fréquentes
    c.execute("CREATE INDEX IF NOT EXISTS idx_completed_tasks_user ON completed_tasks(user_email)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_completed_tasks_house ON completed_tasks(house_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_completed_tasks_date ON completed_tasks(completed_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_completed_tasks_user_date ON completed_tasks(user_email, completed_at)")
    
    # Index sur users pour les lookups rapides
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_house ON users(house_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    
    # Index sur houses
    c.execute("CREATE INDEX IF NOT EXISTS idx_houses_code ON houses(code)")

    conn.commit()
    conn.close()

init_db()

# === CONFIGURATION DU CACHE POUR LES FICHIERS STATIQUES ===
@app.after_request
def add_cache_headers(response):
    """Ajouter des headers de cache pour les fichiers statiques"""
    if 'static' in request.path:
        # Cache les images/avatars pendant 1 semaine
        if any(ext in request.path for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']):
            response.headers['Cache-Control'] = 'public, max-age=604800'  # 7 jours
        # Cache les CSS/JS pendant 1 jour
        elif any(ext in request.path for ext in ['.css', '.js']):
            response.headers['Cache-Control'] = 'public, max-age=86400'  # 1 jour
    return response


def add_default_rewards_if_empty():
    """
    Fonction désactivée - les récompenses par défaut ne sont plus ajoutées automatiquement
    L'ajout de tâches reste actif via les autres fonctions
    """
    pass


add_default_rewards_if_empty()

def get_user_points(email):
    conn = sqlite3.connect(DB)
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
            SELECT DISTINCT DATE(completed_at, 'localtime') as d
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

def create_system_message(house_id, content, message_type='system', related_task_id=None, send_push=True, sender_name=None):
    """
    Crée un message système automatique pour la maison.
    Types: 'system', 'task_completed', 'task_added', 'congratulation', 'reminder', 'sermon'
    
    Si send_push=True, envoie également une notification push aux membres de la maison.
    sender_name: nom personnalisé pour l'expéditeur (ex: nom de la maison)
    """
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        # Utiliser le nom de la maison ou un nom par défaut
        if sender_name is None:
            c.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
            house_row = c.fetchone()
            if house_row:
                sender_name = house_row[0] if house_row[0] else house_row[1]
            if not sender_name:
                sender_name = "Maison"
        
        c.execute("""
            INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, related_task_id)
            VALUES (?, ?, 'house', ?, ?, ?)
        """, (house_id, sender_name, content, message_type, related_task_id))
        message_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # 🔔 Envoyer une notification push si activé
        if send_push:
            try:
                # Déterminer l'icône et le titre selon le type
                notification_icons = {
                    'task_completed': '✅',
                    'task_added': '🆕',
                    'congratulation': '🎉',
                    'reminder': '⏰',
                    'sermon': '🏠'
                }
                icon_emoji = notification_icons.get(message_type, '💬')
                
                # Titre personnalisé pour les messages de la maison
                if message_type in ['sermon', 'congratulation', 'reminder']:
                    title = f'{icon_emoji} {sender_name or "Maison"}'
                else:
                    title = f'{icon_emoji} CleanBeat'
                
                notification_data = {
                    'title': title,
                    'body': content,
                    'icon': '/static/images/logo.png',
                    'url': '/comments',
                    'messageId': message_id,
                    'messageType': message_type
                }
                
                # Envoyer à tous les membres de la maison
                notify_house_members(house_id, notification_data)
                
            except Exception as e:
                print(f"⚠️ Erreur envoi notification push: {e}")
        
        return True
    except Exception as e:
        print(f"Erreur création message système: {e}")
        return False

def get_unread_message_count(user_email, house_id):
    """
    Retourne le nombre de messages non lus pour un utilisateur dans sa maison.
    """
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM messages m
            WHERE m.house_id = ?
            AND m.id NOT IN (
                SELECT message_id FROM message_reads WHERE user_email = ?
            )
            AND (m.sender_email IS NULL OR m.sender_email != ?)
        """, (house_id, user_email, user_email))
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def mark_message_as_read(message_id, user_email):
    """
    Marque un message comme lu pour un utilisateur.
    """
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO message_reads (message_id, user_email)
            VALUES (?, ?)
        """, (message_id, user_email))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# 🔔 ========== FONCTIONS PUSH NOTIFICATIONS ==========

def save_push_subscription(user_email, subscription_data):
    """
    Sauvegarde une subscription push pour un utilisateur.
    subscription_data doit contenir: endpoint, keys.p256dh, keys.auth
    """
    try:
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur sauvegarde push subscription: {e}")
        return False


def get_user_push_subscriptions(user_email):
    """
    Récupère toutes les subscriptions push actives d'un utilisateur.
    """
    try:
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur récupération subscriptions: {e}")
        return []


def get_house_push_subscriptions(house_id, exclude_email=None):
    """
    Récupère toutes les subscriptions push des membres d'une maison.
    exclude_email: optionnel, pour exclure l'expéditeur du message
    """
    try:
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur récupération subscriptions maison: {e}")
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
        from pywebpush import webpush, WebPushException
        import json
        
        # VAPID keys - À GÉNÉRER ET STOCKER DE MANIÈRE SÉCURISÉE
        # Pour générer: from pywebpush import webpush; webpush.generate_vapid_keys()
        VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
        VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
        VAPID_CLAIMS = {
            "sub": "mailto:contact@cleanbeat.app"
        }
        
        if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
            print("⚠️ VAPID keys non configurées - notifications push désactivées")
            return False
        
        payload = json.dumps(notification_data)
        
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
        
        return True
        
    except WebPushException as e:
        print(f"❌ WebPush erreur: {e}")
        
        # Si l'abonnement est invalide (410 Gone), le désactiver
        if e.response and e.response.status_code == 410:
            deactivate_push_subscription(subscription.get('endpoint'))
        
        return False
    except ImportError:
        print("⚠️ pywebpush non installé - exécutez: pip install pywebpush")
        return False
    except Exception as e:
        print(f"❌ Erreur envoi push: {e}")
        return False


def deactivate_push_subscription(endpoint):
    """
    Désactive une subscription push (quand elle est invalide/expirée).
    """
    try:
        conn = sqlite3.connect(DB)
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
    
    success_count = 0
    for sub in subscriptions:
        if send_push_notification(sub, notification_data):
            success_count += 1
    
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
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur envoi encouragement maison: {e}")
        return False


def send_house_sermon(house_id, player_name=None, sermon_type='lazy'):
    """
    Envoie un message humoristique de réprimande de la maison.
    sermon_type: 'lazy' (inactivité générale) ou 'funny' (ciblé sur un joueur)
    """
    try:
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur envoi sermon maison: {e}")
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
        conn = sqlite3.connect(DB)
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
                GROUP BY u.email
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
        print(f"❌ Erreur vérification activité maison: {e}")
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
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur création reminder: {e}")
        return None


def get_pending_reminders():
    """
    Récupère les rappels en attente d'envoi.
    """
    from datetime import datetime
    
    conn = sqlite3.connect(DB)
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
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur envoi reminder: {e}")
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
    conn = sqlite3.connect(DB)
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
        
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur update reminder settings: {e}")
        return False


# 💬 ========== FIN SYSTÈME DE RAPPELS ==========


def get_house_players_points(house_id):
    """
    Retourne une liste de dictionnaires avec les joueurs de la maison.
    Inclut automatiquement les daily_points (points du jour) et daily_tasks.
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = date.today().isoformat()
    
    # Récupérer tous les champs nécessaires pour les avatars
    try:
        c.execute("""
            SELECT email, points, avatar, avatar_file, avatar_url, name, player_color, avatar_style
            FROM users WHERE house_id=?
        """, (house_id,))
    except sqlite3.OperationalError:
        # Anciennes bases sans colonne `avatar_style`
        c.execute("""
            SELECT email, points, avatar, avatar_file, avatar_url, name, player_color
            FROM users WHERE house_id=?
        """, (house_id,))
    rows = c.fetchall()
    players = []
    
    for r in rows:
        email = r[0]
        points = r[1]
        avatar_emoji = r[2]
        avatar_file = r[3]
        avatar_url = r[4]
        name = r[5] if r[5] else (email.split('@')[0] if email else '')
        player_color = r[6] if len(r) > 6 else None
        avatar_style = r[7] if len(r) > 7 else None
        
        # Assigner une couleur si le joueur n'en a pas encore
        if not player_color:
            player_color = assign_player_color(email, house_id)

        # Vérifier que avatar_emoji est bien un emoji et pas un nom de fichier/URL
        is_valid_emoji = False
        if avatar_emoji:
            avatar_str = str(avatar_emoji).strip()
            # C'est un emoji si : max 4 caractères, contient des caractères Unicode > 127, 
            # et ne contient pas .png, .jpg, http, ou /
            if (len(avatar_str) <= 4 and 
                any(ord(c) > 127 for c in avatar_str) and
                '.png' not in avatar_str.lower() and 
                '.jpg' not in avatar_str.lower() and
                'http' not in avatar_str.lower() and
                '/' not in avatar_str):
                is_valid_emoji = True

        # Calculer les points du jour (daily_points) avec heure locale
        daily_points = 0
        daily_tasks = 0
        try:
            c.execute("""
                SELECT COALESCE(SUM(points),0), COUNT(*) 
                FROM completed_tasks 
                WHERE user_email=? AND DATE(completed_at, 'localtime')=?
            """, (email, today))
            sums = c.fetchone()
            if sums:
                daily_points = int(sums[0]) if sums[0] is not None else 0
                daily_tasks = int(sums[1]) if sums[1] is not None else 0
        except Exception:
            pass

        # Nettoyer avatar_file et avatar_url des valeurs "None" (chaîne)
        clean_avatar_file = avatar_file if avatar_file and avatar_file != 'None' else None
        clean_avatar_url = avatar_url if avatar_url and avatar_url != 'None' else None

        # Le champ `avatar` peut contenir :
        # - un emoji (is_valid_emoji True)
        # - un seed DiceBear (chaîne sans '.' ni 'http')
        # - un nom de fichier (contient une extension)
        # - une URL (contient 'http')
        raw_avatar = avatar_emoji if avatar_emoji and avatar_emoji != 'None' else None

        # Si `raw_avatar` ressemble à une URL, l'utiliser comme avatar_url
        if raw_avatar and ('http' in raw_avatar.lower() or raw_avatar.startswith('data:')):
            clean_avatar_url = raw_avatar
        # Si `raw_avatar` ressemble à un fichier (contient une extension), le traiter comme avatar_file
        elif raw_avatar and ('.png' in raw_avatar.lower() or '.jpg' in raw_avatar.lower() or '.jpeg' in raw_avatar.lower() or '.svg' in raw_avatar.lower() or '/' in raw_avatar):
            clean_avatar_file = raw_avatar
        # Si `raw_avatar` est un emoji valide, on le conservera dans 'avatar' (is_valid_emoji True)
        # Sinon, s'il y a une chaîne sans extension, on la traite comme seed DiceBear
        elif raw_avatar and not is_valid_emoji:
            seed = raw_avatar
            # Construire l'URL DiceBear en utilisant le style renseigné par l'utilisateur
            style_to_use = avatar_style if avatar_style else 'lorelei'
            clean_avatar_url = f'https://api.dicebear.com/7.x/{style_to_use}/svg?seed={seed}'

        # Si aucun avatar n'est défini après tout, générer une URL DiceBear par défaut basée sur l'email
        if not clean_avatar_url and not clean_avatar_file and not is_valid_emoji:
            seed = email.split('@')[0] if email else 'default'
            style_to_use = avatar_style if avatar_style else 'lorelei'
            clean_avatar_url = f'https://api.dicebear.com/7.x/{style_to_use}/svg?seed={seed}'
        
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
        
        players.append({
            'email': email,
            'name': name,
            'avatar': raw_avatar if raw_avatar else None,  # Peut être emoji ou seed ou filename
            'avatar_url': clean_avatar_url,  # URL si présente (DiceBear ou fournie)
            'avatar_file': clean_avatar_file,  # Fichier uploadé
            'avatar_style': avatar_style,
            'points': points,
            'daily_points': daily_points,
            'daily_tasks': daily_tasks,
            'color': color_vertical if color_vertical else player_color,  # Gradient pour v-bar verticale (ou hex en fallback)
            'color_h': color_horizontal if color_horizontal else player_color,  # Gradient pour v-bar horizontale (ou hex en fallback)
            'player_color_hex': player_color  # Couleur hex brute pour bordure d'avatar
        })

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
    """Inscription avec récupération de mail"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validations
        if not name or not email or not password:
            flash("Tous les champs sont requis", "danger")
            return render_template('signup_email.html')
        
        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères", "danger")
            return render_template('signup_email.html')
            
        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas", "danger")
            return render_template('signup_email.html')
        
        # Vérifier si email existe déjà
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT email FROM users WHERE email=?", (email,))
        if c.fetchone():
            flash("Cet email est déjà utilisé", "danger")
            conn.close()
            return render_template('signup_email.html')
        
        try:
            # Créer l'utilisateur temporaire sans house_id
            hashed_password = generate_password_hash(password)
            c.execute("""
                INSERT INTO users (name, email, password, points, avatar, registration_step) 
                VALUES (?, ?, ?, 0, '👤', 'email_signup')
            """, (name, email, hashed_password))
            
            conn.commit()
            conn.close()
            
            # Sauvegarder dans la session
            session.permanent = True  # Session persistante après rafraîchissement
            session['user'] = email
            session['user_name'] = name
            session['registration_step'] = 'email_signup'
            
            flash(f"Compte créé avec succès ! Bienvenue {name} !", "success")
            return redirect(url_for('invite_partner'))
            
        except sqlite3.IntegrityError:
            flash("Erreur lors de la création du compte", "danger")
            conn.close()
            return render_template('signup_email.html')
    
    return render_template('signup_email.html')

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
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name, password FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[1], password):
        session.permanent = True  # Session persistante après rafraîchissement
        session['user'] = email
        session['user_name'] = user[0]
        flash(f"🎉 Re-bienvenue {user[0]} ! Prêt(e) pour de nouvelles aventures ? 🚀", "success")
        return redirect(url_for('menu'))
    else:
        flash("🚫 Email ou mot de passe incorrect ! Vérifie tes infos !", "danger")
        return render_template('quick_login.html')


# Register

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Finaliser la création du profil avec photo/avatar"""
    if 'user' not in session:
        flash("Veuillez d'abord vous inscrire", "warning")
        return redirect(url_for('signup_email'))

    if request.method == 'POST':
        photo_data = request.form.get('photo_data')
        avatar = request.form.get('avatar')
        name = request.form.get('name', '').strip()
        if not name or (not avatar and not photo_data):
            flash("Veuillez entrer un prénom et choisir un avatar ou une photo.", "danger")
            return render_template('create_profile.html')

        photo_filename = None
        if photo_data:
            photo_filename = save_photo_from_base64(photo_data)
            if not photo_filename:
                flash("Erreur lors de la sauvegarde de la photo.", "danger")
                return render_template('create_profile.html')

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        # Mettre à jour le profil utilisateur
        update_query = "UPDATE users SET name=?, avatar=?, registration_step=? WHERE email=?"
        update_values = [name, avatar, 'profile_created', session['user']]
        c.execute(update_query, update_values)
        # Si photo, enregistrer le fichier
        if photo_filename:
            c.execute("UPDATE users SET avatar_file=? WHERE email=?", (photo_filename, session['user']))
        # Vérifier/Créer maison si besoin
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        if not user_house or not user_house[0]:
            house_code = generate_house_code()
            # Créer la maison sans nom pour forcer le formulaire sur /menu
            c.execute("INSERT INTO houses (name, house_name, level, health, mood, code, progress) VALUES (?, ?, 1, 100, 'happy', ?, 0)", ('', '', house_code))
            house_id = c.lastrowid
            c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, session['user']))
        conn.commit()
        conn.close()
        session['user_name'] = name
        session['registration_step'] = 'profile_created'
        flash(f"Profil créé! Bienvenue {name} !", "success")
        return redirect(url_for('menu'))

    return render_template('create_profile.html')


# ========================================
# Routes pour la gestion des joueurs
# ========================================

@app.route('/manage_players')
def manage_players():
    """Page de gestion des joueurs de la maison"""
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB)
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
    
    # Récupérer tous les joueurs de cette maison
    c.execute("""
        SELECT email, name, avatar, avatar_file, avatar_url, player_color
        FROM users
        WHERE house_id=?
        ORDER BY name
    """, (house_id,))
    
    players = []
    for row in c.fetchall():
        email, name, avatar, avatar_file, avatar_url, player_color = row
        
        # Assigner une couleur si le joueur n'en a pas encore
        if not player_color:
            player_color = assign_player_color(email, house_id)
        
        players.append({
            'email': email,
            'name': name,
            'avatar': avatar,
            'avatar_file': avatar_file,
            'avatar_url': avatar_url,
            'color': player_color
        })
    
    conn.close()
    
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
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Vérifier que l'utilisateur actuel et le joueur à modifier sont dans la même maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_house = c.fetchone()
    
    c.execute("SELECT house_id, email, name, avatar, avatar_file, avatar_url FROM users WHERE email=?", (email,))
    player_row = c.fetchone()
    
    if not user_house or not player_row or user_house[0] != player_row[0]:
        conn.close()
        flash("Non autorisé", "error")
        return redirect(url_for('manage_players'))
    
    player = {
        'email': player_row[1],
        'name': player_row[2],
        'avatar': player_row[3],
        'avatar_file': player_row[4],
        'avatar_url': player_row[5]
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
        
        conn = sqlite3.connect(DB)
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
        
        return jsonify({'success': True, 'message': 'Nom de la maison mis à jour !'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/update_player', methods=['POST'])
def update_player():
    """Mettre à jour le nom et l'avatar d'un joueur"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'})
    
    try:
        email = request.form.get('email')
        name = request.form.get('name', '').strip()
        avatar_type = request.form.get('avatar_type')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email requis'})
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        # Vérifier que l'utilisateur actuel et le joueur à modifier sont dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        
        c.execute("SELECT house_id FROM users WHERE email=?", (email,))
        player_house = c.fetchone()
        
        if not user_house or not player_house or user_house[0] != player_house[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        # Préparer la mise à jour
        update_parts = []
        update_values = []
        
        if name:
            update_parts.append("name=?")
            update_values.append(name)
        
        # Gérer l'avatar
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
        
        elif avatar_type == 'dicebear':
            # Avatar DiceBear : récupérer le seed et construire l'URL
            seed = request.form.get('avatar', '').strip()
            style = request.form.get('avatar_style', 'avataaars').strip()
            if seed:
                dicebear_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={seed}"
                update_parts.append("avatar_url=?")
                update_values.append(dicebear_url)
                # Effacer les autres types d'avatar
                update_parts.append("avatar=?")
                update_values.append(None)
                update_parts.append("avatar_file=?")
                update_values.append(None)
        
        elif avatar_type == 'file':
            # Sélection d'une image PNG existante depuis la galerie
            avatar_filename = request.form.get('avatar', '').strip()
            if avatar_filename and avatar_filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                update_parts.append("avatar_file=?")
                update_values.append(avatar_filename)
                # Effacer les autres types d'avatar
                update_parts.append("avatar=?")
                update_values.append(None)
                update_parts.append("avatar_url=?")
                update_values.append(None)
        
        elif avatar_type == 'photo':
            # Gérer l'upload de fichier
            if 'avatar_file' in request.files:
                file = request.files['avatar_file']
                if file and file.filename:
                    # Sauvegarder le fichier
                    filename = secure_filename(file.filename)
                    timestamp = int(time.time())
                    unique_filename = f"{timestamp}_{filename}"
                    filepath = os.path.join('static', 'avatars', unique_filename)
                    
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    file.save(filepath)
                    
                    update_parts.append("avatar_file=?")
                    update_values.append(unique_filename)
                    # Effacer les autres types d'avatar
                    update_parts.append("avatar=?")
                    update_values.append(None)
                    update_parts.append("avatar_url=?")
                    update_values.append(None)
        
        if update_parts:
            update_values.append(email)
            query = f"UPDATE users SET {', '.join(update_parts)} WHERE email=?"
            c.execute(query, update_values)
            conn.commit()
            
            # 🔌 WEBSOCKET: Notifier tous les joueurs du changement d'avatar
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    socketio.emit('avatar_updated', {'email': email}, namespace='/')
                    print(f"🔌 WebSocket: Diffusion changement avatar pour {email}")
                except Exception as ws_err:
                    print(f"⚠️ Erreur WebSocket avatar: {ws_err}")
        
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"[ERROR update_player] {e}")
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
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        # Vérifier que l'utilisateur actuel et le joueur à supprimer sont dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        
        c.execute("SELECT house_id FROM users WHERE email=?", (email,))
        player_house = c.fetchone()
        
        if not user_house or not player_house or user_house[0] != player_house[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        # Supprimer le joueur de la maison (mettre house_id à NULL)
        c.execute("UPDATE users SET house_id=NULL WHERE email=?", (email,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"[ERROR delete_player] {e}")
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
    
    conn = sqlite3.connect(DB)
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
            if avatar_file:
                player1_avatar_url = url_for('static', filename='avatars/' + avatar_file)
        
        # Points du jour pour le joueur actuel
        from datetime import date
        today = date.today().isoformat()
        c.execute("SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at, 'localtime')=?", (session['user'], today))
        pts = c.fetchone()
        current_user_daily_points = int(pts[0]) if pts and pts[0] else 0
        
        # Ajouter les points du jour à chaque joueur
        for p in players:
            email = p.get('email')
            if email:
                c.execute("SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at, 'localtime')=?", (email, today))
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
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        # Récupérer la maison du parent
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        parent = c.fetchone()
        
        if not parent or not parent[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Vous devez avoir une maison'})
        
        house_id = parent[0]
        child_name = request.form.get('child_name', '').strip()
        
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
                print(f"✅ [ADD_CHILD] Avatar DiceBear: {avatar_url}")
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
            avatar_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={default_seed}"
            avatar = default_seed[:8]
        
        # Créer un email unique pour l'enfant (interne, pas utilisé pour connexion)
        child_email = f"child_{house_id}_{int(time.time())}@cleanbeat.internal"
        
        # Insérer l'enfant dans la base
        c.execute("""
            INSERT INTO users (email, name, avatar, avatar_file, avatar_url, house_id, password)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
        """, (child_email, child_name, avatar, avatar_file, avatar_url, house_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Enfant ajouté'})
        
    except Exception as e:
        print(f"[ERROR add_child] {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/comments', methods=['GET','POST'])
def comments():
    """
    Messagerie améliorée avec:
    - Messages entre joueurs de la maison
    - Messages automatiques (tâches validées/ajoutées)
    - Système de lu/non-lu
    - Badge de notification
    """
    if 'user' not in session:
        flash("Connecte-toi pour accéder à la messagerie", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB)
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
                
                # Notifier le destinataire via WebSocket
                # Compter le nombre de messages non lus pour le destinataire
                unread_count = get_unread_message_count(recipient_email, house_id)
                
                # Émettre l'événement WebSocket au destinataire
                socketio.emit('new_message_notification', {
                    'sender': current_user_name,
                    'content': content[:50] + ('...' if len(content) > 50 else ''),
                    'unread_count': unread_count,
                    'recipient_email': recipient_email
                }, room=f'house_{house_id}')
                
                flash(f"Message envoyé à {recipient[1] if recipient[1] else recipient[0]}", "success")
            else:
                flash("Destinataire invalide.", "danger")
        else:
            flash("Veuillez sélectionner un destinataire et écrire un message.", "danger")
        
        return redirect(url_for('comments'))

    # Récupérer les messages privés (envoyés ou reçus par l'utilisateur connecté)
    # ET les messages de la maison (sender_type = 'house')
    c.execute("""
        SELECT m.id, m.sender_email, m.recipient_email, m.content, m.timestamp, m.sender_type, m.message_type,
               sender.name, sender.avatar, sender.avatar_file, sender.avatar_url,
               recipient.name, recipient.avatar, recipient.avatar_file, recipient.avatar_url
        FROM messages m
        LEFT JOIN users sender ON m.sender_email = sender.email
        LEFT JOIN users recipient ON m.recipient_email = recipient.email
        WHERE m.house_id = ? 
        AND (
            (m.message_type = 'private' AND (m.sender_email = ? OR m.recipient_email = ?))
            OR m.sender_type = 'house'
        )
        ORDER BY m.timestamp DESC
        LIMIT 100
    """, (house_id, session['user'], session['user']))
    
    messages_data = []
    for row in c.fetchall():
        msg_id, sender_email, recipient_email, content, timestamp, sender_type, message_type, sender_name, sender_avatar, sender_avatar_file, sender_avatar_url, recipient_name, recipient_avatar, recipient_avatar_file, recipient_avatar_url = row
        
        # Marquer le message comme lu pour l'utilisateur actuel
        if sender_email != session['user']:
            mark_message_as_read(msg_id, session['user'])
        
        # Préparer l'avatar et nom de l'expéditeur
        if sender_type == 'house':
            # Message de la maison - utiliser l'avatar maison
            display_sender_avatar = '🏠'
            # sender_email contient le nom de la maison pour les messages 'house'
            sender_name = sender_email if sender_email else house_name
        else:
            # Message d'un utilisateur
            display_sender_avatar = None
            if sender_avatar_file:
                display_sender_avatar = f"/static/uploads/{sender_avatar_file}"
            elif sender_avatar_url:
                display_sender_avatar = sender_avatar_url
            elif sender_avatar and len(str(sender_avatar)) <= 4:
                display_sender_avatar = sender_avatar
            else:
                display_sender_avatar = '👤'
            
            if not sender_name:
                sender_name = sender_email.split('@')[0] if sender_email else 'Inconnu'
        
        # Préparer l'avatar du destinataire
        display_recipient_avatar = None
        if recipient_avatar_file:
            display_recipient_avatar = f"/static/uploads/{recipient_avatar_file}"
        elif recipient_avatar_url:
            display_recipient_avatar = recipient_avatar_url
        elif recipient_avatar and len(str(recipient_avatar)) <= 4:
            display_recipient_avatar = recipient_avatar
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
            'is_me': sender_email == session['user']
        })
    
    # Après avoir marqué les messages comme lus, mettre à jour le compteur et notifier via WebSocket
    unread_count = get_unread_message_count(session['user'], house_id)
    socketio.emit('unread_count_update', {
        'count': unread_count,
        'user_email': session['user']
    }, room=f'house_{house_id}')
    
    # Récupérer le code de la maison
    c.execute("SELECT code, name FROM houses WHERE id=?", (house_id,))
    house_row = c.fetchone()
    house_code = house_row[0] if house_row else None
    house_name = house_row[1] if house_row and house_row[1] else 'Ma Maison'
    
    # Récupérer tous les joueurs de la maison (sauf l'utilisateur actuel)
    print(f"[DEBUG COMMENTS] house_id={house_id}, current_user={session['user']}")
    c.execute("""
        SELECT email, name, avatar, avatar_file, avatar_url
        FROM users 
        WHERE house_id = ? 
        AND email != ?
    """, (house_id, session['user']))
    
    available_players = []
    players_result = c.fetchall()
    print(f"[DEBUG COMMENTS] Nombre de joueurs trouvés: {len(players_result)}")
    
    for player_row in players_result:
        player_email, player_name, player_avatar, player_avatar_file, player_avatar_url = player_row
        print(f"[DEBUG COMMENTS] Joueur: {player_name} ({player_email})")
        
        # Préparer l'avatar
        display_avatar = None
        if player_avatar_file:
            display_avatar = f"/static/uploads/{player_avatar_file}"
        elif player_avatar_url:
            display_avatar = player_avatar_url
        elif player_avatar and len(str(player_avatar)) <= 4:
            display_avatar = player_avatar
        else:
            display_avatar = '👤'
        
        available_players.append({
            'email': player_email,
            'name': player_name if player_name else player_email.split('@')[0],
            'avatar': display_avatar
        })
    
    print(f"[DEBUG COMMENTS] available_players count: {len(available_players)}")
    
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
            # Messages de la maison - couleur or/jaune
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
                         unread_count=unread_count)


@app.route('/rewards')
def rewards():
    if 'user' not in session:
        flash("Connecte-toi pour accéder aux récompenses", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        flash("Tu dois rejoindre une maison pour accéder aux récompenses", "warning")
        return redirect(url_for('menu'))
    
    house_id = user_row[0]
    user_name = user_row[1]
    
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
            AND DATE(ct.completed_at, 'localtime') >= ?
        WHERE u.house_id = ?
        GROUP BY u.email
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
    
    # Ajouter la colonne week_start si elle n'existe pas
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN week_start DATE")
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
    
    # Récupérer le type de foyer
    c.execute("SELECT house_type FROM houses WHERE id=?", (house_id,))
    house_type_row = c.fetchone()
    house_type = house_type_row[0] if house_type_row and house_type_row[0] else 'family'
    
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
    rewards_family_list = json.loads(family_custom[0]) if family_custom else default_rewards_family
    rewards_couple_list = json.loads(couple_custom[0]) if couple_custom else default_rewards_couple
    rewards_coloc_list = json.loads(coloc_custom[0]) if coloc_custom else default_rewards_coloc

    
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
    
    conn = sqlite3.connect(DB)
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
    
    conn = sqlite3.connect(DB)
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
            AND DATE(ct.completed_at, 'localtime') >= ?
        WHERE u.house_id = ?
        GROUP BY u.email
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
    
    print(f"[DEBUG open_reward_box] house_id={house_id}, house_type={house_type}, box_number={box_number}")
    
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
    
    print(f"[DEBUG] Recherche custom_rewards: house_id={house_id}, house_type={house_type}")
    print(f"[DEBUG] custom_rewards_row trouvé: {custom_rewards_row is not None}")
    
    if custom_rewards_row:
        # Utiliser les récompenses personnalisées
        custom_rewards_list = json.loads(custom_rewards_row[0])
        rewards = [{"text": reward, "image": None} for reward in custom_rewards_list]
        print(f"[DEBUG] Utilisation de {len(rewards)} récompenses personnalisées")
    else:
        # Utiliser les récompenses par défaut selon le type de foyer
        if house_type == 'couple':
            rewards = default_rewards_couple
            print(f"[DEBUG] Utilisation des récompenses par défaut COUPLE")
        elif house_type == 'coloc':
            rewards = default_rewards_coloc
            print(f"[DEBUG] Utilisation des récompenses par défaut COLOC")
        else:
            rewards = default_rewards_family
            print(f"[DEBUG] Utilisation des récompenses par défaut FAMILLE")
    
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
        print(f"[DEBUG] Insertion dans mystery_rewards: user={session['user']}, house={house_id}, reward={reward_text}")
        c.execute("""
            INSERT INTO mystery_rewards (user_email, house_id, reward_text, won_date, used)
            VALUES (?, ?, ?, date('now'), 0)
        """, (session['user'], house_id, reward_text))
        
        conn.commit()
        print(f"[DEBUG] Récompense enregistrée avec succès!")
    except Exception as e:
        conn.close()
        print(f"[ERROR] Erreur lors de l'insertion: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur base de données: {str(e)}'}), 500
    
    conn.close()
    
    # Récupérer le nom de l'utilisateur
    user_name = session.get('user_name', '')
    if not user_name:
        conn2 = sqlite3.connect(DB)
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
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_row = c.fetchone()
    if not house_row or not house_row[0]:
        conn.close()
        flash("Vous devez rejoindre une maison", "warning")
        return redirect(url_for('menu'))
    
    house_id = house_row[0]
    
    print(f"[DEBUG mes_recompenses] house_id={house_id}, user={session['user']}")
    
    # Récupérer tous les joueurs de la maison avec leurs récompenses
    c.execute("""
        SELECT u.email, u.name, u.avatar, u.avatar_file
        FROM users u
        WHERE u.house_id=?
        ORDER BY u.name
    """, (house_id,))
    
    players_data = []
    for player_row in c.fetchall():
        player_email = player_row[0]
        player_name = player_row[1]
        player_avatar = player_row[2]
        player_avatar_file = player_row[3]
        
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
        
        print(f"[DEBUG] Joueur {player_name} ({player_email}): {len(available)} récompenses disponibles")
        
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
            'avatar': player_avatar,
            'avatar_file': player_avatar_file,
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
    
    print(f"[DEBUG use_reward] reward_id={reward_id}, user={session['user']}")
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Vérifier que la récompense appartient à l'utilisateur
    c.execute("""
        SELECT id FROM mystery_rewards
        WHERE id=? AND user_email=? AND used=0
    """, (reward_id, session['user']))
    
    reward_row = c.fetchone()
    print(f"[DEBUG] Récompense trouvée: {reward_row is not None}")
    
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
    print(f"[DEBUG] Lignes modifiées: {rows_affected}")
    
    conn.commit()
    conn.close()
    
    print(f"[DEBUG] Récompense {reward_id} marquée comme utilisée avec succès")
    
    return jsonify({'success': True})


@app.route('/buy_reward/<int:reward_id>')
def buy_reward(reward_id):
    # Fonctionnalité temporairement désactivée
    return redirect(url_for('menu'))
    
    if 'user' not in session:
        flash("Connecte-toi pour acheter une récompense", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB)
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
    """Grille de cadeaux CleanBeat - débloquée le dimanche matin"""
    if 'user' not in session:
        flash("🔐 Connecte-toi pour voir tes cadeaux !", "warning")
        return redirect(url_for('signup_email'))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Récupérer house_id de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_id = c.fetchone()[0]
    
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
    
    conn = sqlite3.connect(DB)
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
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT password, registration_step, avatar, avatar_file FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[0], password):
            session.permanent = True  # Session persistante après rafraîchissement
            session['user'] = email
            
            # Vérifier si l'utilisateur a complété son profil
            registration_step = user[1] or ''
            avatar = user[2] or ''
            avatar_file = user[3] or ''
            
            # Si le profil n'est pas complété (pas de registration_step='profile_created' OU pas d'avatar)
            if registration_step != 'profile_created' or (not avatar and not avatar_file):
                flash("✨ Complétez votre profil pour commencer !", "info")
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


# Page Mon Profil (glassmorphisme)
@app.route('/profile')
def profile():
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Récupérer les infos utilisateur
    c.execute("SELECT name, email, avatar, avatar_file, house_id FROM users WHERE email=?", (session['user'],))
    user = c.fetchone()
    
    if not user:
        conn.close()
        flash("Utilisateur non trouvé", "danger")
        return redirect(url_for('login'))
    
    user_name, user_email, user_avatar, user_photo, house_id = user
    
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
                           house_name=house_name,
                           house_code=house_code)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('login'))
    
    name = request.form.get('name', '').strip()
    avatar = request.form.get('avatar', '').strip()
    avatar_style = request.form.get('avatar_style', '').strip()
    photo_data = request.form.get('photo_data')
    house_name_input = request.form.get('house_name', '').strip()
    
    # Debug: afficher ce qui est reçu
    print(f"[DEBUG update_profile] name='{name}', avatar='{avatar}' (len={len(avatar) if avatar else 0}), photo_data={'oui' if photo_data else 'non'}")
    
    # Déterminer si l'avatar est un fichier PNG ou un emoji
    avatar_is_file = avatar and (avatar.endswith('.png') or avatar.endswith('.jpg') or avatar.endswith('.jpeg'))
    avatar_is_emoji = avatar and not avatar_is_file
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Construire la requête de mise à jour
    update_parts = []
    update_values = []
    
    # Toujours mettre à jour le nom s'il est fourni
    if name:
        update_parts.append("name=?")
        update_values.append(name)
        session['user_name'] = name
    
    # Gérer l'avatar selon son type
    if avatar_is_file:
        # C'est un fichier PNG du dossier avatars -> stocker dans avatar_file
        update_parts.append("avatar_file=?")
        update_values.append(avatar)
        update_parts.append("avatar=?")
        update_values.append('')  # Vider le champ emoji
        session['user_avatar'] = avatar
        if 'user_photo' in session:
            del session['user_photo']
    elif avatar_is_emoji:
        # C'est un emoji -> stocker dans avatar
        update_parts.append("avatar=?")
        update_values.append(avatar)
        update_parts.append("avatar_file=?")
        update_values.append(None)  # Vider le champ fichier
        session['user_avatar'] = avatar
        if 'user_photo' in session:
            del session['user_photo']
    else:
        # Peut être un seed DiceBear -> stocker avatar (seed) et avatar_style
        if avatar and not avatar_is_file and not avatar_is_emoji:
            update_parts.append("avatar=?")
            update_values.append(avatar)
            update_parts.append("avatar_style=?")
            update_values.append(avatar_style if avatar_style else 'lorelei')
            update_parts.append("avatar_file=?")
            update_values.append(None)
            if 'user_photo' in session:
                del session['user_photo']
    
    # Traiter la photo uploadée (priorité maximale)
    if photo_data and photo_data.startswith('data:image'):
        photo_filename = save_photo_from_base64(photo_data)
        if photo_filename:
            update_parts.append("avatar_file=?")
            update_values.append(photo_filename)
            update_parts.append("avatar=?")
            update_values.append('')  # Vider le champ emoji
            session['user_photo'] = photo_filename
    
    if update_parts:
        update_values.append(session['user'])
        try:
            c.execute(f"UPDATE users SET {', '.join(update_parts)} WHERE email=?", update_values)
        except sqlite3.OperationalError as e:
            # Ajouter la colonne avatar_style si nécessaire puis réessayer
            if 'no such column' in str(e):
                try:
                    c.execute("ALTER TABLE users ADD COLUMN avatar_style TEXT")
                    conn.commit()
                except Exception:
                    pass
                c.execute(f"UPDATE users SET {', '.join(update_parts)} WHERE email=?", update_values)
            else:
                raise
    
    # Mettre à jour le nom de la maison si fourni
    if house_name_input:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        if user_house and user_house[0]:
            c.execute("UPDATE houses SET house_name=?, name=? WHERE id=?", 
                      (house_name_input, house_name_input, user_house[0]))
    
    conn.commit()
    conn.close()
    
    flash("Profil mis à jour avec succès ! ✨", "success")
    return redirect(url_for('menu'))


# Routes pour la création de profil
@app.route('/create_profile')
def create_profile():
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('signup_email'))
    
    # Vérifier si l'utilisateur a déjà un profil (mode modification)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name, avatar, avatar_file, house_id, registration_step FROM users WHERE email=?", (session['user'],))
    user = c.fetchone()
    
    change_avatar = False
    current_name = ''
    current_avatar = ''
    current_avatar_file = ''
    current_house_name = ''
    
    if user:
        current_name = user[0] or ''
        current_avatar = user[1] or ''  # Avatar prédéfini (nom de fichier comme homme.png)
        current_avatar_file = user[2] or ''  # Photo uploadée (fichier JPG)
        house_id = user[3]
        registration_step = user[4] or ''
        
        # Si l'utilisateur a COMPLÉTÉ son profil (registration_step='profile_created'), c'est une modification
        # Sinon, c'est toujours une première création même si le nom existe
        if registration_step == 'profile_created':
            change_avatar = True
        
        # Récupérer le nom de la maison si existe
        if house_id:
            c.execute("SELECT house_name FROM houses WHERE id=?", (house_id,))
            house = c.fetchone()
            if house and house[0]:
                current_house_name = house[0]
    
    conn.close()
    
    return render_template('create_profile.html', 
                           change_avatar=change_avatar,
                           current_name=current_name,
                           current_avatar=current_avatar,
                           current_avatar_file=current_avatar_file,
                           current_house_name=current_house_name)

@app.route('/create_profile', methods=['POST'])
def create_profile_post():
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('signup_email'))
    
    name = request.form.get('name', '').strip()
    bio = request.form.get('bio', '').strip()
    avatar = request.form.get('avatar', '').strip()
    avatar_style = request.form.get('avatar_style', 'avataaars').strip()
    photo_data = request.form.get('photo_data')
    house_name_input = request.form.get('house_name', '').strip()
    
    if not name:
        flash("Le nom est requis", "danger")
        return render_template('create_profile.html')
    
    photo_filename = None
    if photo_data and photo_data.startswith('data:image'):
        photo_filename = save_photo_from_base64(photo_data)
        if not photo_filename:
            flash("Erreur lors de la sauvegarde de la photo", "warning")
    
    # Déterminer si l'avatar est un fichier PNG, emoji ou DiceBear (seed)
    avatar_is_file = avatar and (avatar.endswith('.png') or avatar.endswith('.jpg') or avatar.endswith('.jpeg'))
    avatar_is_emoji = avatar and len(avatar) <= 4 and not avatar_is_file  # Emoji court
    avatar_is_dicebear = avatar and not avatar_is_file and not avatar_is_emoji  # Seed DiceBear
    
    # Mettre à jour le profil utilisateur
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    update_values = [name]
    update_query = "UPDATE users SET name=?"
    
    if bio:
        update_query += ", bio=?"
        update_values.append(bio)
    
    # Si l'avatar est un fichier PNG du dossier avatars, le stocker dans avatar_file
    if avatar_is_file:
        update_query += ", avatar_file=?, avatar=?, avatar_url=?"
        update_values.append(avatar)
        update_values.append('')  # Vider le champ avatar emoji
        update_values.append('')  # Vider avatar_url
    elif avatar_is_emoji:
        # C'est un emoji, le stocker dans avatar
        update_query += ", avatar=?, avatar_file=?, avatar_url=?"
        update_values.append(avatar)
        update_values.append('')  # Vider le champ avatar_file
        update_values.append('')  # Vider avatar_url
    elif avatar_is_dicebear:
        # C'est un seed DiceBear. Stocker le seed dans la colonne `avatar`
        # (le template `menu.html` détecte un seed sans extension et construit
        # l'URL DiceBear côté client en utilisant le style `lorelei` par défaut).
        # Construire aussi l'URL DiceBear côté serveur pour éviter les champs vides
        style_to_use = avatar_style if avatar_style else 'lorelei'
        avatar_url_built = f'https://api.dicebear.com/7.x/{style_to_use}/svg?seed={avatar}'
        update_query += ", avatar=?, avatar_file=?, avatar_url=?"
        update_values.append(avatar)           # stocke le seed (ex: 'abc123')
        update_values.append('')               # vider avatar_file
        update_values.append(avatar_url_built) # stocke avatar_url construit
        
    if photo_filename:
        # Une photo uploadée remplace tout
        update_query += ", avatar_file=?, avatar=?, avatar_url=?, avatar_style=?"
        update_values.append(photo_filename)
        update_values.append('')  # Vider le champ avatar emoji
        update_values.append('')  # Vider avatar_url
        update_values.append('')  # Vider avatar_style
    else:
        # Toujours sauvegarder le style choisi si fourni
        update_query += ", avatar_style=?"
        update_values.append(avatar_style)
    
    update_query += ", registration_step=? WHERE email=?"
    update_values.extend(['profile_created', session['user']])
    
    try:
        c.execute(update_query, update_values)
    except sqlite3.OperationalError as e:
        # Si la colonne `avatar_style` n'existe pas, la créer puis réessayer
        if 'no such column' in str(e):
            try:
                c.execute("ALTER TABLE users ADD COLUMN avatar_style TEXT")
                conn.commit()
            except Exception:
                pass
            c.execute(update_query, update_values)
        else:
            raise
    
    # Vérifier si l'utilisateur a déjà une maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_house = c.fetchone()
    
    if not user_house or not user_house[0]:
        # Créer une nouvelle maison sans nom pour forcer le formulaire sur /menu
        from datetime import date
        house_code = generate_house_code()
        today = date.today().isoformat()
        c.execute("""
            INSERT INTO houses (name, house_name, level, health, mood, code, progress, last_reset_date) 
            VALUES (?, ?, 1, 0, 'happy', ?, 0, ?)
        """, ('', '', house_code, today))
        house_id = c.lastrowid
        c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, session['user']))
        # Commit immédiatement après création de la maison
        conn.commit()
    else:
        conn.commit()
    
    conn.close()
    
    # Sauvegarde des informations dans la session
    session['user_name'] = name
    session['user_photo'] = photo_filename
    session['registration_step'] = 'profile_created'

    # Mettre à jour des clés de session pour que l'avatar soit disponible immédiatement
    try:
        # Priorité: photo uploadée > fichier avatar dans /static/avatars > emoji > DiceBear seed/url
        if photo_filename:
            session['user_avatar'] = photo_filename
            session['user_avatar_url'] = url_for('static', filename=f'avatars/{photo_filename}')
        else:
            if avatar_is_file:
                session['user_avatar'] = avatar
                session['user_avatar_url'] = url_for('static', filename=f'avatars/{avatar}')
            elif avatar_is_emoji:
                session['user_avatar'] = avatar
                session.pop('user_avatar_url', None)
            elif avatar_is_dicebear:
                session['user_avatar'] = avatar
                session['user_avatar_url'] = avatar_url_built
            else:
                # fallback
                session.pop('user_avatar', None)
                session.pop('user_avatar_url', None)
    except Exception:
        # Ne pas bloquer la création de profil si session/url_for pose problème
        pass
    
    if photo_filename:
        flash(f"Profil créé avec succès pour {name} avec photo!", "success")
    else:
        flash(f"Profil créé avec succès pour {name}!", "success")

    # Debug: afficher ce qui a été sauvegardé (temporaire)
    try:
        debug_msg = f"DEBUG avatar enregistré: user={session.get('user')}, avatar={avatar}, avatar_style={avatar_style}, avatar_file={photo_filename if photo_filename else ''}, avatar_url={avatar_url if 'avatar_url' in locals() else ''}"
        print(debug_msg)
        flash(debug_msg, "info")
    except Exception:
        pass

    # Redirect vers /menu en ajoutant un cookie temporaire contenant l'URL d'aperçu
    resp = redirect(url_for('menu'))
    try:
        preview_url = None
        if session.get('user_avatar_url'):
            preview_url = session.get('user_avatar_url')
        elif 'avatar_url_built' in locals():
            preview_url = avatar_url_built
        if preview_url:
            # Cookie courte durée pour que la page /menu côté client puisse appliquer l'avatar immédiatement
            resp.set_cookie('preview_avatar_url', preview_url, max_age=300, path='/')
    except Exception:
        pass

    return resp


@app.route('/join_house', methods=['GET', 'POST'])
def join_house():
    if request.method == 'POST':
        house_code = request.form.get('house_code', '').strip().upper()
        user_name = request.form.get('user_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        # Vérifier que tous les champs sont remplis (house_name retiré)
        if not all([house_code, user_name, email, password]):
            flash("Tous les champs sont requis.", "danger")
            return render_template('join_house.html')
        
        # Vérifier que le mot de passe fait au moins 6 caractères
        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
            return render_template('join_house.html')
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        try:
            # Vérifier que le code de maison existe
            c.execute("SELECT id, name FROM houses WHERE code=?", (house_code,))
            house_row = c.fetchone()
            
            if not house_row:
                flash("Code de maison invalide. Vérifiez le code et réessayez.", "danger")
                conn.close()
                return render_template('join_house.html')
            
            house_id = house_row[0]
            
            # Vérifier que l'email n'existe pas déjà
            c.execute("SELECT email FROM users WHERE email=?", (email,))
            if c.fetchone():
                flash("Cet email est déjà utilisé. Connectez-vous ou utilisez un autre email.", "danger")
                conn.close()
                return render_template('join_house.html')
            
            # Ne plus mettre à jour le nom de la maison ici - ce sera fait plus tard
            
            # Créer le nouvel utilisateur
            hashed_password = generate_password_hash(password)
            c.execute("""
                INSERT INTO users (email, password, name, house_id, points, avatar)
                VALUES (?, ?, ?, ?, 0, '🧑')
            """, (email, hashed_password, user_name, house_id))
            
            conn.commit()
            conn.close()
            
            # Connecter automatiquement l'utilisateur
            session.permanent = True  # Session persistante après rafraîchissement
            session['user'] = email
            session['name'] = user_name
            
            flash(f"🎉 Bienvenue {user_name} ! Créez maintenant votre profil et choisissez votre avatar !", "success")
            return redirect(url_for('create_profile'))
            
        except Exception as e:
            conn.close()
            print(f"Erreur lors de la création du compte: {e}")
            flash("Une erreur s'est produite. Veuillez réessayer.", "danger")
            return render_template('join_house.html')
    
    return render_template('join_house.html')


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
    conn = sqlite3.connect(DB)
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
    
    if request.method == 'POST':
        import json
        partners_data = request.form.get('partners')
        children_data = request.form.get('children')
        
        sent_count = 0
        children_created = 0
        
        # Récupérer le nom de l'utilisateur actuel
        user_name = session.get('user', 'Un ami')
        if 'user' in session:
            conn = sqlite3.connect(DB)
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
                
                # Envoyer un SMS à chaque partenaire
                for partner in partners:
                    try:
                        send_sms_invitation(
                            partner['phone'], 
                            user_name,
                            house_code
                        )
                        sent_count += 1
                    except Exception as e:
                        print(f"Erreur lors de l'envoi du SMS à {partner['name']}: {e}")
                    
            except Exception as e:
                print(f"Erreur lors du traitement des partenaires: {e}")
        
        # Traiter les enfants (création de comptes)
        if children_data and house_id:
            try:
                children = json.loads(children_data)
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                
                for child in children:
                    try:
                        child_name = child.get('name', '').strip()
                        child_avatar = child.get('avatar', '👶')  # Avatar par défaut si non spécifié
                        if child_name:
                            # Créer un email fictif pour l'enfant (basé sur le nom + timestamp)
                            import time
                            child_email = f"child_{child_name.lower().replace(' ', '_')}_{int(time.time())}@cleanbeat.local"
                            
                            # Créer le compte enfant avec l'avatar choisi
                            c.execute("""
                                INSERT INTO users (email, name, house_id, points, avatar, is_child_account, created_by)
                                VALUES (?, ?, ?, 0, ?, 1, ?)
                            """, (child_email, child_name, house_id, child_avatar, session.get('user', '')))
                            children_created += 1
                    except Exception as e:
                        print(f"Erreur lors de la création du compte enfant {child.get('name', '')}: {e}")
                
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Erreur lors du traitement des enfants: {e}")
        
        # Messages flash
        messages = []
        if sent_count > 0:
            messages.append(f"📱 {sent_count} invitation{'s' if sent_count > 1 else ''} SMS envoyée{'s' if sent_count > 1 else ''}")
        if children_created > 0:
            messages.append(f"👶 {children_created} profil{'s' if children_created > 1 else ''} enfant{'s' if children_created > 1 else ''} créé{'s' if children_created > 1 else ''}")
        
        if messages:
            flash("🎉 " + " • ".join(messages), "success")
        elif not partners_data and not children_data:
            flash("Tu pourras inviter des partenaires plus tard depuis ton profil !", "info")
        else:
            flash("Aucune invitation n'a pu être envoyée.", "warning")
        
        # Continuer vers la création de profil
        return redirect(url_for('create_profile'))
    
    # Si accès direct à la page (GET), afficher la page d'invitation simple avec QR Code
    # Construire l'URL d'invitation
    join_url = f"http://192.168.1.156:8000/join_house?code={house_code}"
    
    # Choisir le template selon si on vient du processus d'inscription ou si on veut juste inviter
    # Pour l'instant, on affiche toujours le formulaire complet
    return render_template('invite_partner_new.html', 
                         house_code=house_code, 
                         house_name=house_name, 
                         house_type=house_type,
                         join_url=join_url)


@app.route('/partager_invitation')
def partager_invitation():
    """Page simple pour partager l'invitation avec QR Code"""
    if 'user' not in session:
        flash("Connecte-toi pour inviter des partenaires !", "warning")
        return redirect(url_for('login'))
    
    # Récupérer le code et le nom de la maison
    conn = sqlite3.connect(DB)
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
    join_url = f"http://192.168.1.156:8000/join_house?code={house_code}"
    
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
    
    conn = sqlite3.connect(DB)
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
    conn = sqlite3.connect(DB)
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
    from flask import render_template, session
    import sqlite3
    players = []
    current_user_name = session.get('user', '')
    # Récupérer les joueurs de la maison si l'utilisateur est connecté
    if 'user' in session:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        
        # Si l'utilisateur n'a pas de maison, rediriger vers la page d'invitation
        if not row or not row[0]:
            conn.close()
            flash("Crée ou rejoins une maison pour commencer à jouer ! 🏠", "info")
            return redirect(url_for('invite_partner'))
        
        if row and row[0]:
            house_id = row[0]
            # Réinitialisation quotidienne de la santé/progression de la maison
            try:
                from datetime import date
                today = date.today().isoformat()
                c.execute("SELECT health, last_reset_date FROM houses WHERE id=?", (house_id,))
                hrow = c.fetchone()
                if hrow:
                    current_last_reset = hrow[1]
                    if current_last_reset != today:
                        # reset santé à 0 en début de journée
                        c.execute("UPDATE houses SET health=?, last_reset_date=? WHERE id=?", (0, today, house_id))
                        conn.commit()
            except Exception:
                # Fallback: utiliser progress si health indisponible
                try:
                    from datetime import date
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
            players = get_house_players_points(house_id)
            # Ajouter les streaks pour chaque joueur
            try:
                for p in players:
                    p['streak'] = compute_daily_streak(conn, p.get('email'))
            except Exception:
                pass
            # Ajouter activité du jour (points et nombre de tâches) pour chaque joueur
            try:
                from datetime import date
                today = date.today().isoformat()
                for p in players:
                    email = p.get('email')
                    if not email:
                        p['daily_points'] = 0
                        p['daily_tasks'] = 0
                        continue
                    # Utiliser l'heure locale pour éviter les décalages de fuseau horaire
                    c.execute("SELECT COALESCE(SUM(points),0), COUNT(*) FROM completed_tasks WHERE user_email=? AND DATE(completed_at, 'localtime')=?", (email, today))
                    sums = c.fetchone()
                    p['daily_points'] = int(sums[0]) if sums and sums[0] is not None else 0
                    p['daily_tasks'] = int(sums[1]) if sums and sums[1] is not None else 0
            except Exception:
                # En cas d'erreur, initialiser à zéro
                for p in players:
                    p['daily_points'] = 0
                    p['daily_tasks'] = 0
        conn.close()
    # Récupérer le nom de la maison (afficher le formulaire si aucun des deux champs n'est rempli)
    house_name = None
    show_house_name_form = False
    show_intro_message = False
    house_health = None
    daily_report = []
    if 'user' in session:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if row and row[0]:
            house_id = row[0]
            try:
                c.execute("SELECT name, house_name, health FROM houses WHERE id=?", (house_id,))
                house_row = c.fetchone()
            except sqlite3.OperationalError:
                # Compatibilité anciennes bases sans colonne 'health'
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
                    # Afficher house_name si présent, sinon name
                    house_name = house_name_db.strip() if house_name_db and house_name_db.strip() else name.strip() if name and name.strip() else None
                    # Afficher le message d'introduction si la maison vient d'être nommée (paramètre URL)
                    if request.args.get('welcome') == '1':
                        show_intro_message = True

            # Rapport quotidien des tâches effectuées (par joueurs)
            try:
                # Rapport du jour en heure locale via SQLite
                c.execute("""
                    SELECT user_email, category, task_name, points, completed_at
                    FROM completed_tasks
                    WHERE house_id=?
                      AND datetime(completed_at) >= datetime(date('now','localtime'))
                      AND datetime(completed_at) < datetime(date('now','localtime','+1 day'))
                    ORDER BY completed_at DESC
                """, (house_id,))
                rows = c.fetchall()
                # Fallback basique si rien (sans conversion locale)
                if not rows:
                    c.execute("""
                        SELECT user_email, category, task_name, points, completed_at
                        FROM completed_tasks
                        WHERE house_id=?
                          AND date(completed_at) = date('now')
                        ORDER BY completed_at DESC
                    """, (house_id,))
                    rows = c.fetchall()
                # Diagnostic: si toujours vide, récupérer les 5 dernières tâches de la maison
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
                # Récupérer noms et avatars des joueurs
                email_to_name = {}
                email_to_avatar = {}
                try:
                    c.execute("SELECT email, name, avatar, avatar_file, avatar_url, avatar_style FROM users WHERE house_id=?", (house_id,))
                    for e, n, avatar, avatar_file, avatar_url, avatar_style in c.fetchall():
                        email_to_name[e] = n if n else (e.split('@')[0] if e else '')
                        # Résoudre l'URL d'avatar (priorité: avatar_file > avatar_url > seed/filename > dicebear par défaut)
                        final_url = None
                        if avatar_file:
                            try:
                                final_url = url_for('static', filename=f'avatars/{avatar_file}')
                            except Exception:
                                final_url = None
                        if not final_url and avatar_url:
                            final_url = avatar_url
                        if not final_url and avatar:
                            # Si c'est une URL complète
                            if isinstance(avatar, str) and avatar.startswith('http'):
                                final_url = avatar
                            else:
                                # Si semble être un nom de fichier (contient un point), servir depuis static
                                if isinstance(avatar, str) and '.' in avatar:
                                    final_url = url_for('static', filename=f'avatars/{avatar}')
                                else:
                                    # Traiter comme seed DiceBear et respecter le style stocké
                                    style = avatar_style if avatar_style else 'lorelei'
                                    final_url = f'https://api.dicebear.com/7.x/{style}/svg?seed={avatar}'
                        if not final_url:
                            # Générer une URL DiceBear par défaut basée sur l'email
                            seed = e.split('@')[0] if e else 'default'
                            final_url = f'https://api.dicebear.com/7.x/lorelei/svg?seed={seed}'
                        email_to_avatar[e] = final_url
                except sqlite3.OperationalError:
                    # Anciennes bases sans colonne avatar_file/avatar_style
                    c.execute("SELECT email, name, avatar, avatar_url FROM users WHERE house_id=?", (house_id,))
                    for e, n, avatar, avatar_url in c.fetchall():
                        email_to_name[e] = n if n else (e.split('@')[0] if e else '')
                        final_url = None
                        if avatar_url:
                            final_url = avatar_url
                        elif avatar:
                            # Si avatar est numérique index -> use helper
                            try:
                                idx = int(avatar)
                                final_url = get_avatar_url(idx)
                            except (ValueError, TypeError):
                                if isinstance(avatar, str) and avatar.startswith('http'):
                                    final_url = avatar
                                elif isinstance(avatar, str) and '.' in avatar:
                                    final_url = url_for('static', filename=f'avatars/{avatar}')
                                else:
                                    # seed DiceBear fallback to lorelei
                                    final_url = f'https://api.dicebear.com/7.x/lorelei/svg?seed={avatar}'
                        if not final_url:
                            final_url = url_for('static', filename='avatars/homme.png')
                        email_to_avatar[e] = final_url
                daily_report = [
                    {
                        'email': r[0],
                        'name': email_to_name.get(r[0], r[0]),
                        'avatar_url': email_to_avatar.get(r[0], url_for('static', filename='avatars/homme.png')),
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
                            'avatar_url': email_to_avatar.get(r[0], url_for('static', filename='avatars/homme.png')),
                            'category': r[1],
                            'task_name': r[2],
                            'points': r[3],
                            'completed_at': r[4]
                        }
                        for r in diag_rows
                    ]
            except Exception:
                daily_report = []
        conn.close()
    # Préparer les données header: joueur courant et joueur en attente
    player1_name = None
    player1_points = 0
    player1_avatar_url = None
    player1_avatar = None
    player1_avatar_file = None
    player2_name = None
    player2_points = 0
    player2_avatar_url = None

    if players:
        # Identifier le joueur courant dans la liste
        current_email = session.get('user')
        current_player = None
        for p in players:
            if p.get('email') == current_email:
                current_player = p
                break
        # Joueur courant = player1
        if current_player:
            player1_name = current_player.get('name')
            player1_points = current_player.get('daily_points', 0)  # Utiliser daily_points
            player1_avatar_url = current_player.get('avatar_url')
            player1_avatar = current_player.get('avatar')
            player1_avatar_file = current_player.get('avatar_file')
        else:
            # fallback si non trouvé
            p0 = players[0]
            player1_name = p0.get('name')
            player1_points = p0.get('daily_points', 0)  # Utiliser daily_points
            player1_avatar_url = p0.get('avatar_url')
            player1_avatar = p0.get('avatar')
            player1_avatar_file = p0.get('avatar_file')
        # Joueur en attente = premier autre joueur de la maison
        others = [p for p in players if p.get('email') != current_email]
        if others:
            p2 = others[0]
            player2_name = p2.get('name')
            player2_points = p2.get('daily_points', 0)  # Utiliser daily_points
            player2_avatar_url = p2.get('avatar_url')
    
# 🎨 Créer une map de couleurs cohérente pour tous les joueurs
    if players:
        player_emails = [p.get('email') for p in players if p.get('email')]
        color_map = get_player_colors_map(player_emails)
        
        # Assigner les couleurs à chaque joueur
        for player in players:
            email = player.get('email')
            if email and email in color_map:
                player['color'] = color_map[email]['vertical']
                player['color_h'] = color_map[email]['horizontal']
            else:
                player['color'] = 'linear-gradient(180deg, #95A5A6 0%, #7F8C8D 100%)'
                player['color_h'] = 'linear-gradient(90deg, #95A5A6 0%, #7F8C8D 100%)'

    from flask import make_response
    
    # 🔔 Compter les messages non lus pour l'utilisateur
    unread_messages_count = 0
    if 'user' in session:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house_row = c.fetchone()
        if user_house_row and user_house_row[0]:
            unread_messages_count = get_unread_message_count(session['user'], user_house_row[0])
        conn.close()
    
    # Si l'avatar du joueur courant est manquant dans la liste, utiliser la valeur en session (mise à jour après création de profil)
    try:
        if not player1_avatar_url and session.get('user_avatar_url'):
            player1_avatar_url = session.get('user_avatar_url')
    except Exception:
        pass

    resp = make_response(render_template(
        'menu.html',
        players=players,
        current_user_name=current_user_name,
        current_user_daily_points=next((p.get('daily_points',0) for p in players if p.get('email')==current_user_name), 0),
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
    ))
    # Désactiver le cache pour éviter d'afficher d'anciennes valeurs de daily_points
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


# Simple route de test pour vérifier la connectivité (retourne OK en texte brut)
@app.route('/ping')
def ping():
    return 'OK', 200, {'Content-Type': 'text/plain; charset=utf-8'}

# Endpoint de debug pour vérifier les daily_points calculés côté serveur
@app.route('/debug_points')
def debug_points():
    if 'user' not in session:
        return {'error': 'Non connecté', 'redirect': '/login'}, 401
    conn = sqlite3.connect(DB)
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
        c.execute("SELECT COALESCE(SUM(points),0), COUNT(*) FROM completed_tasks WHERE user_email=? AND DATE(completed_at, 'localtime')=?", (email, today))
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
        conn = sqlite3.connect(DB)
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

    return render_template('tasks.html', category=cat, category_name=category_name, category_icon=category_icon, tasks_with_images=tasks_with_images, tasks_points=tasks_points, custom_tasks=custom_tasks, players=players, hide_header=True)


# --- Routes minimales pour éviter les erreurs de BuildError dans tasks.html ---

# Dictionnaire des noms et icônes de catégories
CATEGORY_NAMES = {
    'salon': ('Salon', '🛋️'),
    'cuisine': ('Cuisine', '🍳'),
    'buanderie': ('Buanderie', '👕'),
    'toilettes': ('Toilettes', '🚽'),
    'chambre': ('Chambre Parentale', '🛏️'),
    'salle_bain': ('Salle de bain', '🛁'),
    'chambre_enfant': ('Chambre Enfant', '🧸'),
    'chambre_bebe': ('Chambre Bébé', '👶'),
    'chambre_ado': ('Zone Ados', '🎮'),
    'piece_bonus': ('Pièce Bonus', '💎'),
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
    conn = sqlite3.connect(DB)
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
                
                message_content = f"🆕 {creator_name} a ajouté une nouvelle tâche : '{task_name}' ({points} pts)"
                create_system_message(house_id, message_content, 'task_added')
            except Exception:
                pass  # Ne pas bloquer si le message échoue
            
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

    conn = sqlite3.connect(DB)
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

    conn = sqlite3.connect(DB)
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
    
    conn = sqlite3.connect(DB)
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
        c.execute("SELECT SUM(points), COUNT(*) FROM completed_tasks WHERE user_email=? AND DATE(completed_at, 'localtime')=?", (session['user'], today))
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
        
        # Vérifier doublon
        c.execute("SELECT id FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at, 'localtime')=?", (session['user'], category, task_name, today))
        if c.fetchone():
            funny_messages = [
                f"✅ Tu as déjà validé '{task_name}' aujourd'hui ! Une fois suffit 😊",
                f"🎯 '{task_name}' c'est fait ! Passe à autre chose champion(ne) ! 💪",
                f"⚡ Déjà validé ! Tu es tellement efficace que tu oublies ce que tu as fait 😄",
                f"🏆 '{task_name}' : CHECK ! Pas besoin de le refaire, promis !",
            ]
            flash(random.choice(funny_messages), "warning")
            conn.close()
            return redirect(url_for('menu'))
        
        # Récupérer le joueur qui a fait la tâche (depuis le formulaire)
        player_email = request.form.get('player_email', session['user'])
        
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
            
            # 🔌 WEBSOCKET: Notifier tous les joueurs de la mise à jour des points
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    # Récupérer les données de tous les joueurs pour mise à jour immédiate
                    c_ws = conn.cursor()
                    c_ws.execute("""
                        SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
                               COALESCE(SUM(ct.points), 0) as daily_points
                        FROM users u
                        LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                            AND DATE(ct.completed_at, 'localtime') = DATE('now', 'localtime')
                        WHERE u.house_id = ?
                        GROUP BY u.email
                        ORDER BY daily_points DESC, u.points DESC
                    """, (user_house_id,))
                    players_data = []
                    for p in c_ws.fetchall():
                        players_data.append({
                            'email': p[0],
                            'name': p[1],
                            'avatar': p[2],
                            'avatar_url': p[3],
                            'avatar_file': p[4],
                            'total_points': p[5] or 0,
                            'daily_points': int(p[6]) if p[6] else 0
                        })
                    
                    # Utiliser socketio.emit() directement pour émettre depuis une route HTTP
                    socketio.emit('players_points_update', {
                        'players': players_data,
                        'updated_player': player_email
                    }, namespace='/', room=f'house_{user_house_id}')
                    print(f"🔌 WebSocket: Diffusion mise à jour points pour {player_email} (room: house_{user_house_id})")
                except Exception as ws_err:
                    print(f"⚠️ Erreur WebSocket points: {ws_err}")
            
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
            
            # 🎯 Créer un message automatique pour notifier les autres joueurs
            try:
                message_content = f"✅ {player_name} a validé '{task_name}' (+{task_points} pts)"
                create_system_message(user_house_id, message_content, 'task_completed')
                
                # 💬 Envoyer un message de félicitation si le joueur a fait 3 tâches ou plus aujourd'hui
                try:
                    today = date.today().isoformat()
                    c_check = conn.cursor()
                    c_check.execute("""
                        SELECT COUNT(*) FROM completed_tasks 
                        WHERE user_email=? AND DATE(completed_at, 'localtime')=?
                    """, (player_email, today))
                    task_count = c_check.fetchone()[0]
                    
                    if task_count >= 3 and task_count % 3 == 0:  # À chaque multiple de 3
                        congrats_msg = get_house_personality_message('congratulation', player_name)
                        create_system_message(user_house_id, congrats_msg, 'congratulation')
                except Exception:
                    pass  # Ne pas bloquer si ça échoue
                    
            except Exception:
                pass  # Ne pas bloquer si le message échoue
            
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
                          is_custom_task=True)


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
        conn = sqlite3.connect(DB)
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
            c.execute("SELECT SUM(points), COUNT(*) FROM completed_tasks WHERE user_email=? AND DATE(completed_at, 'localtime')=?", (session['user'], today))
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

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        # Récupérer le joueur qui a fait la tâche (depuis le formulaire)
        player_email = request.form.get('player_email', session['user'])
        
        # LOGS DE DEBUG
        print(f"🎯 [VALIDATION] Utilisateur connecté: {session['user']}")
        print(f"🎯 [VALIDATION] Joueur sélectionné (player_email): {player_email}")
        print(f"🎯 [VALIDATION] Tâche: {task_name} ({task_points} pts)")
        
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
        # éviter doublons sur la même journée pour la même tâche
        # Vérifier doublon sur la journée locale POUR LE JOUEUR QUI VALIDE
        c.execute("SELECT id FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at, 'localtime')=?", (player_email, normalized_cat, task_name, today))
        if c.fetchone():
            # 🎭 Messages humoristiques personnalisés selon la tâche
            funny_messages = {
                # Lit / Chambre
                'lit': [
                    "🛏️ Ton lit est déjà fait ! À moins que tu ne veuilles dormir dedans et le refaire ? 😴",
                    "🛏️ Le lit est nickel ! Pas besoin de le border 47 fois par jour 😄",
                    "🛏️ Hé oh, le lit ne va pas se défaire tout seul ! Enfin... sauf si tu fais une sieste 💤",
                ],
                'ranger': [
                    "🧹 C'est déjà rangé ! Tu es sûr(e) de ne pas être un peu maniaque ? 😅",
                    "📦 Tout est en place ! Respire, détends-toi, c'est propre !",
                    "🗂️ Déjà fait ! Tu veux qu'on range les rangements ? 🤔",
                ],
                'vaisselle': [
                    "🍽️ La vaisselle est déjà propre ! Propose plutôt à ton/ta partenaire de la faire demain 😉",
                    "🧽 Hé, la vaisselle brille déjà ! Tu veux laver l'éponge aussi ? 😄",
                    "🍽️ C'est fait ! Si tu t'ennuies, tu peux toujours faire un gâteau... et salir de la vaisselle 🎂",
                ],
                'aspirateur': [
                    "🧹 Aspirer 2 fois par jour, c'est être maniaque niveau expert ! 🏆",
                    "🧹 L'aspirateur a besoin de repos aussi ! Laisse-le souffler 😅",
                    "🧹 Déjà passé ! Les moutons de poussière n'ont pas eu le temps de revenir 🐑",
                ],
                'balai': [
                    "🧹 Balayer deux fois dans la journée, c'est être maniaque ! Les poussières te remercient 😄",
                    "🧹 Le sol est nickel ! Tu attends de la visite royale ? 👑",
                    "🧹 Déjà balayé ! À ce rythme, tu vas user le carrelage 😅",
                ],
                'courses': [
                    "🛒 Tu as déjà fait les courses ! Le frigo est plein, profites-en 🥗",
                    "🛒 Courses faites ! Sauf si tu as oublié quelque chose... encore ? 😏",
                    "🛒 Déjà validé ! Tu veux vraiment y retourner ? Le supermarché va fermer 🏪",
                ],
                'cuisine': [
                    "👨‍🍳 La cuisine est propre ! Tu veux cuisiner pour salir et recommencer ? 🍳",
                    "🍳 Plan de travail nickel ! Pas touche, c'est beau comme ça ✨",
                    "👨‍🍳 Déjà nettoyé ! Ton/ta partenaire peut prendre le relais demain 😉",
                ],
                'poubelle': [
                    "🗑️ Poubelle déjà sortie ! Elle ne se remplit pas si vite (enfin j'espère) 😄",
                    "🗑️ C'est fait ! À moins que tu aies jeté quelque chose d'important ? 🤔",
                    "🗑️ Validé ! Les éboueurs te remercient pour ta ponctualité 🚛",
                ],
                'linge': [
                    "👕 Le linge est déjà lavé ! Tu veux te salir pour en refaire ? 😅",
                    "🧺 Machine faite ! Tes vêtements te disent merci 👔",
                    "👕 Déjà validé ! Le sèche-linge a besoin de repos 💨",
                ],
                'café': [
                    "☕ Le café est fait ! Tu en veux un autre ? Attention à la caféine 😄",
                    "☕ Déjà préparé ! À ce rythme, tu ne dormiras plus jamais 😴",
                    "☕ C'est validé ! Machine à café = meilleure amie 🤝",
                ],
            }
            
            # Messages génériques par défaut
            generic_messages = [
                f"✅ Tu as déjà validé '{task_name}' aujourd'hui ! Une fois suffit 😊",
                f"🎯 '{task_name}' c'est fait ! Passe à autre chose champion(ne) ! 💪",
                f"⚡ Déjà validé ! Tu es tellement efficace que tu oublies ce que tu as fait 😄",
                f"🏆 '{task_name}' : CHECK ! Pas besoin de le refaire, promis !",
                f"😎 Relax ! '{task_name}' est déjà dans ta liste de victoires du jour !",
            ]
            
            # Trouver un message approprié
            task_lower = task_name.lower()
            selected_messages = generic_messages
            
            for keyword, messages in funny_messages.items():
                if keyword in task_lower:
                    selected_messages = messages
                    break
            
            funny_message = random.choice(selected_messages)
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
            print(f"✅ [VALIDATION] Points attribués à: {player_email}")
            print(f"✅ [VALIDATION] Montant: {final_task_points} points")
            
            # 🔌 WEBSOCKET: Notifier tous les joueurs de la mise à jour des points
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    # Récupérer les données de tous les joueurs pour mise à jour immédiate
                    c_ws = conn.cursor()
                    c_ws.execute("""
                        SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
                               COALESCE(SUM(ct.points), 0) as daily_points
                        FROM users u
                        LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
                            AND DATE(ct.completed_at, 'localtime') = DATE('now', 'localtime')
                        WHERE u.house_id = ?
                        GROUP BY u.email
                        ORDER BY daily_points DESC, u.points DESC
                    """, (house_id,))
                    players_data = []
                    for p in c_ws.fetchall():
                        players_data.append({
                            'email': p[0],
                            'name': p[1],
                            'avatar': p[2],
                            'avatar_url': p[3],
                            'avatar_file': p[4],
                            'total_points': p[5] or 0,
                            'daily_points': int(p[6]) if p[6] else 0
                        })
                    
                    # Utiliser socketio.emit() directement pour émettre depuis une route HTTP
                    socketio.emit('players_points_update', {
                        'players': players_data,
                        'updated_player': player_email
                    }, namespace='/', room=f'house_{house_id}')
                    print(f"🔌 WebSocket: Diffusion mise à jour points pour {player_email} (room: house_{house_id})")
                except Exception as ws_err:
                    print(f"⚠️ Erreur WebSocket points: {ws_err}")
            
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
            
            # 👶 Sauvegarder les données de suivi bébé si présentes
            tracking_time = request.form.get('tracking_time')
            bottle_ml = request.form.get('bottle_ml')
            observations = request.form.get('observations')
            
            if tracking_time:  # Si données de suivi présentes
                try:
                    # Déterminer le type de tâche bébé
                    task_type = None
                    if 'biberon' in task_name.lower():
                        task_type = 'biberon'
                    elif 'couche' in task_name.lower():
                        task_type = 'couches'
                    elif 'dormir' in task_name.lower():
                        task_type = 'sommeil'
                    
                    if task_type:
                        # Sauvegarder dans baby_tracking
                        c.execute("""
                            INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (player_email, house_id, task_type, tracking_time, bottle_ml if bottle_ml else None, observations))
                        conn.commit()
                        
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
                        
                        create_system_message(house_id, message_text, 'baby_tracking')
                except Exception as e:
                    print(f"⚠️ Erreur sauvegarde baby tracking: {e}")
                    # Ne pas bloquer la validation si le tracking échoue
            
            # 🎯 Créer un message automatique pour notifier les autres joueurs
            try:
                message_content = f"✅ {player_name} a validé '{task_name}' (+{final_task_points} pts)"
                create_system_message(house_id, message_content, 'task_completed')
                
                # 💬 Envoyer un message de félicitation si le joueur a fait 3 tâches ou plus aujourd'hui
                try:
                    today = date.today().isoformat()
                    c_check = conn.cursor()
                    c_check.execute("""
                        SELECT COUNT(*) FROM completed_tasks 
                        WHERE user_email=? AND DATE(completed_at, 'localtime')=?
                    """, (player_email, today))
                    task_count = c_check.fetchone()[0]
                    
                    if task_count >= 3 and task_count % 3 == 0:  # À chaque multiple de 3
                        congrats_msg = get_house_personality_message('congratulation', player_name)
                        create_system_message(house_id, congrats_msg, 'congratulation')
                except Exception:
                    pass  # Ne pas bloquer si ça échoue
                    
            except Exception:
                pass  # Ne pas bloquer si le message échoue
            
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
    print(f"🎨 [TASK_ENHANCED] Joueurs passés au template:")
    for p in players:
        print(f"   • {p.get('name', 'N/A')}: color={p.get('color', 'NONE')}")
    
    return render_template('task_page_enhanced.html', task_name=task_name, task_image=task_image, task_points=task_points, task_description=task_description, fun_text=fun_text, ad_text=ad_text, ad_link=ad_link, players=players, daily_points=daily_points, daily_tasks=daily_tasks, total_points=total_points, category=cat, hide_header=True)


# 🎭 API : Récupérer la liste des avatars disponibles
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
        print(f"Erreur lecture dossier avatars: {e}")
    
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
            print(f"Erreur lecture config avatars: {e}")
    
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
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    try:
        # Récupérer house_id de l'utilisateur courant
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'tasks': []}, 200
        
        house_id = row[0]
        
        # Récupérer les tâches du jour avec heure locale
        from datetime import date
        today = date.today().isoformat()
        
        c.execute("""
            SELECT 
                ct.user_email, 
                ct.task_name, 
                ct.points, 
                datetime(ct.completed_at, 'localtime') as completed_at_local,
                u.name,
                u.avatar_url,
                u.avatar_file
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ?
              AND u.house_id = ?
              AND DATE(ct.completed_at, 'localtime') = ?
            ORDER BY ct.completed_at DESC
            LIMIT 10
        """, (house_id, house_id, today))
        
        rows = c.fetchall()
        tasks = []
        
        for row in rows:
            email, task_name, points, completed_at, name, avatar_url, avatar_file = row
            
            # Résoudre l'avatar
            final_avatar = None
            if avatar_file:
                final_avatar = url_for('static', filename=f'avatars/{avatar_file}')
            elif avatar_url:
                final_avatar = avatar_url
            else:
                final_avatar = url_for('static', filename='avatars/homme.png')
            
            # Extraire l'heure de completed_at_local (déjà en heure locale grâce à SQLite)
            try:
                # Format: 2026-01-27 08:50:22 (déjà en heure locale)
                time_str = completed_at.split(' ')[1][:5] if ' ' in completed_at else '??:??'
            except:
                time_str = '??:??'
            
            tasks.append({
                'player_name': name if name else email.split('@')[0],
                'task_name': task_name,
                'points': points,
                'time': time_str,
                'avatar': final_avatar,
                'is_current_user': (email == session['user'])
            })
        
        return {'tasks': tasks}, 200
        
    except Exception as e:
        print(f"Erreur API daily_tasks: {e}")
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
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    try:
        print('DEBUG /api/players_points args:', dict(request.args))
        # Allow debug override: ?house_id=123 to force players response for a house
        house_id_param = request.args.get('house_id')
        if house_id_param:
            try:
                house_id = int(house_id_param)
            except Exception:
                return {'players': [], 'error': 'invalid house_id'}, 400
        else:
            if 'user' not in session:
                return {'players': []}, 200

            # Récupérer house_id de l'utilisateur
            c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
            row = c.fetchone()
            if not row or not row[0]:
                return {'players': []}, 200

            house_id = row[0]
        
        # S'assurer que la colonne `avatar_style` existe (migration idempotente)
        try:
            c.execute("PRAGMA table_info(users)")
            cols = [r[1] for r in c.fetchall()]
            if 'avatar_style' not in cols:
                try:
                    c.execute("ALTER TABLE users ADD COLUMN avatar_style TEXT")
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass

        # Récupérer les points de tous les joueurs avec get_house_players_points
        # If house_id was provided via query param (debug mode), build players directly
        if house_id_param:
            players = []
            try:
                try:
                    c.execute("SELECT email, points, avatar, avatar_file, avatar_url, name, player_color, avatar_style FROM users WHERE house_id=?", (house_id,))
                except sqlite3.OperationalError:
                    c.execute("SELECT email, points, avatar, avatar_file, avatar_url, name, player_color FROM users WHERE house_id=?", (house_id,))
                rows = c.fetchall()
                for r in rows:
                    email = r[0]
                    points = r[1]
                    avatar_emoji = r[2]
                    avatar_file = r[3]
                    avatar_url = r[4]
                    name = r[5] if r[5] else (email.split('@')[0] if email else '')
                    player_color = r[6] if len(r) > 6 else None
                    avatar_style = r[7] if len(r) > 7 else None

                    # determine clean avatar url similar to get_house_players_points
                    clean_avatar_file = avatar_file if avatar_file and avatar_file != 'None' else None
                    clean_avatar_url = avatar_url if avatar_url and avatar_url != 'None' else None
                    raw_avatar = avatar_emoji if avatar_emoji and avatar_emoji != 'None' else None

                    if raw_avatar and ('http' in raw_avatar.lower() or raw_avatar.startswith('data:')):
                        clean_avatar_url = raw_avatar
                    elif raw_avatar and ('.png' in raw_avatar.lower() or '.jpg' in raw_avatar.lower() or '.jpeg' in raw_avatar.lower() or '.svg' in raw_avatar.lower() or '/' in raw_avatar):
                        clean_avatar_file = raw_avatar
                    elif raw_avatar:
                        seed = raw_avatar
                        style_to_use = avatar_style if avatar_style else 'lorelei'
                        clean_avatar_url = f'https://api.dicebear.com/7.x/{style_to_use}/svg?seed={seed}'

                    if not clean_avatar_url and not clean_avatar_file and raw_avatar:
                        seed = email.split('@')[0] if email else 'default'
                        style_to_use = avatar_style if avatar_style else 'lorelei'
                        clean_avatar_url = f'https://api.dicebear.com/7.x/{style_to_use}/svg?seed={seed}'

                    players.append({
                        'email': email,
                        'name': name,
                        'avatar': raw_avatar if raw_avatar else None,
                        'avatar_url': clean_avatar_url,
                        'avatar_file': clean_avatar_file,
                        'avatar_style': avatar_style,
                        'points': points,
                        'daily_points': 0,
                        'daily_tasks': 0
                    })
            except Exception as e:
                print('Erreur debug players build:', e)
        else:
            players = get_house_players_points(house_id)
        
        # Formater pour la réponse API
        players_data = []
        for p in players:
            players_data.append({
                'email': p['email'],
                'name': p['name'],
                'avatar': p.get('avatar'),
                'avatar_url': p.get('avatar_url'),
                'avatar_style': p.get('avatar_style'),
                'avatar_file': p.get('avatar_file'),
                'points': p['points'],
                'daily_points': p.get('daily_points', 0),
                'daily_tasks': p.get('daily_tasks', 0)
            })
        
        # Récupérer la santé de la maison
        c.execute("SELECT health FROM houses WHERE id=?", (house_id,))
        health_row = c.fetchone()
        house_health = health_row[0] if health_row and health_row[0] is not None else 100
        
        return {
            'players': players_data,
            'house_health': house_health
        }, 200
        
    except Exception as e:
        print(f"Erreur API players_points: {e}")
        return {'players': [], 'error': str(e)}, 500
    finally:
        conn.close()


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
        print(f"❌ Erreur API push subscribe: {e}")
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
        print(f"❌ Erreur API push unsubscribe: {e}")
        return {'success': False, 'error': str(e)}, 500


@app.route('/api/push/vapid-public-key')
def api_push_vapid_key():
    """
    Retourne la clé publique VAPID pour les subscriptions push.
    """
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
            'title': '🧹 CleanBeat Test',
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
        print(f"❌ Erreur API push test: {e}")
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
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur test reminder: {e}")
        return {'success': False, 'error': str(e)}, 500


# 💬 ========== FIN ROUTES API RAPPELS ==========

# 👶 ========== ROUTES SUIVI BÉBÉ ==========

@app.route('/baby_tracking/<cat>/<int:task_id>')
def baby_tracking(cat, task_id):
    """Page de suivi pour les tâches de bébé (biberon, couches, sommeil)"""
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
    conn = sqlite3.connect(DB)
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
    
    conn = sqlite3.connect(DB)
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
    
    # Créer le message pour le partenaire
    user_name = session['user'].split('@')[0]
    
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
    
    # Envoyer le message au(x) partenaire(s)
    c.execute("SELECT email FROM users WHERE house_id=? AND email!=?", (house_id, session['user']))
    partners = c.fetchall()
    
    from datetime import datetime
    for partner in partners:
        c.execute("""
            INSERT INTO messages (sender, recipient, message_text, sent_at, house_id)
            VALUES (?, ?, ?, ?, ?)
        """, (session['user'], partner[0], message_text, datetime.now().isoformat(), house_id))
    
    conn.commit()
    conn.close()
    
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
    conn = sqlite3.connect(DB)
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
    join_url = f"http://192.168.1.156:8000/join_house?code={house_code}"
    
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
        print(f'🔌 Client connecté: {request.sid}')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Déconnexion d'un client WebSocket"""
        print(f'❌ Client déconnecté: {request.sid}')
    
    @socketio.on('join_house')
    def handle_join_house(data):
        """Un joueur rejoint la room de sa maison"""
        user_email = data.get('email')
        if not user_email:
            return
        
        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT house_id FROM users WHERE email=?", (user_email,))
            row = c.fetchone()
            conn.close()
            
            if row and row[0]:
                house_id = row[0]
                room = f"house_{house_id}"
                join_room(room)
                emit('joined_room', {'room': room, 'email': user_email})
                print(f'🏠 {user_email} a rejoint la room {room}')
        except Exception as e:
            print(f'❌ Erreur join_house: {e}')
    
    @socketio.on('points_updated')
    def handle_points_updated(data):
        """Diffuser la mise à jour des points à tous les joueurs de la maison"""
        try:
            user_email = data.get('email')
            if not user_email:
                return
            
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT house_id FROM users WHERE email=?", (user_email,))
            row = c.fetchone()
            
            if row and row[0]:
                house_id = row[0]
                room = f"house_{house_id}"
                
                # Récupérer les points de tous les joueurs de la maison
                c.execute("""
                    SELECT email, name, avatar, avatar_url, avatar_file, points, avatar_style 
                    FROM users 
                    WHERE house_id=? 
                    ORDER BY points DESC
                """, (house_id,))
                players = []
                for p in c.fetchall():
                    # Assurer que avatar_url est présent (construire depuis seed si nécessaire)
                    avatar = p[2]
                    avatar_url = p[3]
                    avatar_file = p[4]
                    avatar_style = p[6] if len(p) > 6 else None

                    if (not avatar_url or avatar_url == '') and avatar:
                        try:
                            # si avatar ressemble à une URL ou à un filename, laisser tel quel
                            if isinstance(avatar, str) and (avatar.startswith('http') or '.' in avatar or '/' in avatar):
                                avatar_url = avatar_url  # keep as is
                            else:
                                style = avatar_style if avatar_style else 'lorelei'
                                avatar_url = f'https://api.dicebear.com/7.x/{style}/svg?seed={avatar}'
                        except Exception:
                            avatar_url = avatar_url

                    players.append({
                        'email': p[0],
                        'name': p[1],
                        'avatar': avatar,
                        'avatar_url': avatar_url,
                        'avatar_file': avatar_file,
                        'avatar_style': avatar_style,
                        'points': p[5] or 0
                    })
                
                conn.close()
                
                # Diffuser à tous les clients de la room
                emit('players_points_update', {'players': players}, room=room)
                print(f'📊 Points mis à jour pour la room {room}')
        except Exception as e:
            print(f'❌ Erreur points_updated: {e}')
    
    @socketio.on('avatar_updated')
    def handle_avatar_updated(data):
        """Diffuser le changement d'avatar à tous les joueurs de la maison"""
        try:
            user_email = data.get('email')
            if not user_email:
                return
            
            conn = sqlite3.connect(DB)
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
                print(f'👤 Avatar mis à jour pour {user_email} dans la room {room}')
        except Exception as e:
            print(f'❌ Erreur avatar_updated: {e}')


# 🏠 ========== ROUTES TEST MESSAGES MAISON ==========

@app.route('/test_house_encouragement')
def test_house_encouragement():
    """Route de test pour envoyer un message d'encouragement de la maison"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    try:
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur test encouragement: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/test_house_sermon')
def test_house_sermon():
    """Route de test pour envoyer un sermon humoristique de la maison"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    try:
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur test sermon: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/test_house_sermon_lazy')
def test_house_sermon_lazy():
    """Route de test pour envoyer un sermon général d'inactivité"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'}), 401
    
    try:
        conn = sqlite3.connect(DB)
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
        print(f"❌ Erreur test sermon lazy: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 🏠 ========== FIN ROUTES TEST MESSAGES MAISON ==========


@app.route('/debug/players/<int:house_id>')
def debug_players(house_id):
    """Debug endpoint: retourne rapidement les joueurs d'une maison (format API players)"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    players = []
    try:
        try:
            c.execute("SELECT email, points, avatar, avatar_file, avatar_url, name, player_color, avatar_style FROM users WHERE house_id=?", (house_id,))
        except sqlite3.OperationalError:
            c.execute("SELECT email, points, avatar, avatar_file, avatar_url, name, player_color FROM users WHERE house_id=?", (house_id,))
        rows = c.fetchall()
        for r in rows:
            email = r[0]
            points = r[1]
            avatar_emoji = r[2]
            avatar_file = r[3]
            avatar_url = r[4]
            name = r[5] if r[5] else (email.split('@')[0] if email else '')
            player_color = r[6] if len(r) > 6 else None
            avatar_style = r[7] if len(r) > 7 else None

            clean_avatar_file = avatar_file if avatar_file and avatar_file != 'None' else None
            clean_avatar_url = avatar_url if avatar_url and avatar_url != 'None' else None
            raw_avatar = avatar_emoji if avatar_emoji and avatar_emoji != 'None' else None

            if raw_avatar and ('http' in raw_avatar.lower() or raw_avatar.startswith('data:')):
                clean_avatar_url = raw_avatar
            elif raw_avatar and ('.png' in raw_avatar.lower() or '.jpg' in raw_avatar.lower() or '.jpeg' in raw_avatar.lower() or '.svg' in raw_avatar.lower() or '/' in raw_avatar):
                clean_avatar_file = raw_avatar
            elif raw_avatar and not (raw_avatar and ('.' in raw_avatar or '/' in raw_avatar)):
                seed = raw_avatar
                style_to_use = avatar_style if avatar_style else 'lorelei'
                clean_avatar_url = f'https://api.dicebear.com/7.x/{style_to_use}/svg?seed={seed}'

            if not clean_avatar_url and not clean_avatar_file and not raw_avatar:
                seed = email.split('@')[0] if email else 'default'
                style_to_use = avatar_style if avatar_style else 'lorelei'
                clean_avatar_url = f'https://api.dicebear.com/7.x/{style_to_use}/svg?seed={seed}'

            players.append({
                'email': email,
                'name': name,
                'avatar': raw_avatar if raw_avatar else None,
                'avatar_url': clean_avatar_url,
                'avatar_file': clean_avatar_file,
                'avatar_style': avatar_style,
                'points': points,
                'daily_points': 0,
                'daily_tasks': 0
            })
    except Exception as e:
        print('Erreur debug_players:', e)
    finally:
        conn.close()

    return {'players': players}, 200

if __name__ == '__main__':
    # Affiche la table des routes au démarrage (utile pour debug)
    try:
        print('\n--- Flask URL Map ---')
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule}")
        print('---------------------\n')
    except Exception:
        pass

    # Forcer le port 8000
    chosen_port = 8000
    print(f"Démarrage de CleanBeat sur le port {chosen_port}...")
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