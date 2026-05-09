from flask import (
    Blueprint, session, request, flash,
    redirect, url_for, jsonify,
    render_template
)

stats_bp = Blueprint('stats', __name__)


# ════════════════════════════════════════════════════════════
# 🏆📈 PAGE INTERMÉDIAIRE — Classement & Stats (/classement-stats)
# ════════════════════════════════════════════════════════════

@stats_bp.route('/classement-stats')
def classement_stats():
    """Page intermédiaire qui propose deux liens : Classement et Stats."""
    if 'user' not in session:
        return redirect(url_for('auth.signup_email'))
    return render_template('classement_stats.html')


# ════════════════════════════════════════════════════════════
# 📊 STATS — Page principale (/sats)
# ════════════════════════════════════════════════════════════

@stats_bp.route('/sats')
def sats():
    """
    Page de statistiques avec :
    - Podium des joueurs
    - Historique des tâches du jour par joueur avec heure
    - Détection des tentatives de triche
    - Compte à rebours jusqu'au dimanche (ouverture des cadeaux)
    """
    if 'user' not in session:
        return redirect(url_for('auth.signup_email'))

    from datetime import date, datetime, timedelta
    import sqlite3
    from app import (get_db_connection, now_paris, check_weekly_reset,
                     validate_avatar_file, get_player_color, to_paris, _dbg)

    conn = get_db_connection()
    c = conn.cursor()

    try:
        # Récupérer house_id de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            conn.close()
            flash("Crée ou rejoins une maison pour voir les statistiques ! 🏠", "info")
            return redirect(url_for('house.invite_partner'))

        house_id = row[0]
        today = now_paris().date().isoformat()

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
                    skull_active = datetime.fromisoformat(str(skull_expires_at_raw)) > now_paris()
                except Exception:
                    pass
            # Vérifier si le bonus est actif
            bonus_active = False
            if bonus_expires_at_raw:
                try:
                    bonus_active = datetime.fromisoformat(str(bonus_expires_at_raw)) > now_paris()
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
            week_start = (now_paris().date() - timedelta(days=now_paris().date().weekday())).isoformat()
            c.execute("""
                SELECT COALESCE(SUM(points), 0), COUNT(*)
                FROM completed_tasks
                WHERE user_email=? AND DATE(completed_at) >= ?
            """, (email, week_start))
            weekly = c.fetchone()
            weekly_points = int(weekly[0]) if weekly[0] else 0
            weekly_tasks = int(weekly[1]) if weekly[1] else 0

            # Points du mois (depuis le 1er du mois)
            month_start = now_paris().date().replace(day=1).isoformat()
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
                week_start_offset = (now_paris().date() - timedelta(days=now_paris().date().weekday() + (week_offset - 1) * 7)).isoformat()
                week_end_offset = (now_paris().date() - timedelta(days=now_paris().date().weekday() + (week_offset - 2) * 7)).isoformat()
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

            # Extraire l'heure (compatible str ISO et objet datetime) — conversion UTC→Paris
            try:
                paris_dt = to_paris(completed_at)
                if hasattr(paris_dt, 'strftime'):
                    time_str = paris_dt.strftime('%H:%M')
                else:
                    completed_at_str = str(paris_dt or '')
                    if ' ' in completed_at_str:
                        time_str = completed_at_str.split(' ')[1][:5]
                    elif 'T' in completed_at_str:
                        time_str = completed_at_str.split('T')[1][:5]
                    else:
                        time_str = '??:??'
            except Exception:
                try:
                    fb = to_paris(completed_at)
                    if hasattr(fb, 'strftime'):
                        time_str = fb.strftime('%H:%M')
                    else:
                        completed_at_str = str(fb or '')
                        if ' ' in completed_at_str:
                            time_str = completed_at_str.split(' ')[1][:5]
                        elif 'T' in completed_at_str:
                            time_str = completed_at_str.split('T')[1][:5]
                        else:
                            time_str = '??:??'
                except Exception:
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
        today_date = now_paris().date()
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

        # === RÉCAPITULATIF PAR PIÈCE ===
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
        week_start = (now_paris().date() - timedelta(days=now_paris().date().weekday())).isoformat()
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
        return redirect(url_for('menu') + '?nav=1')


# ════════════════════════════════════════════════════════════
# 📈 STATS GRAPHIQUE — Graphiques détaillés
# ════════════════════════════════════════════════════════════

@stats_bp.route('/stats_graphique')
def stats_graphique():
    """Page de statistiques avec graphiques détaillés"""
    if 'user' not in session:
        return redirect(url_for('auth.signup_email'))

    from datetime import date, datetime, timedelta
    import sqlite3
    from app import (get_db_connection, now_paris, check_weekly_reset, _dbg)

    conn = get_db_connection()
    c = conn.cursor()

    try:
        # Récupérer house_id de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            conn.close()
            flash("Crée ou rejoins une maison pour voir les statistiques ! 🏠", "info")
            return redirect(url_for('house.invite_partner'))

        house_id = row[0]
        today = now_paris().date()
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
        return redirect(url_for('stats.sats'))


# ════════════════════════════════════════════════════════════
# 🏆 CLASSEMENT — Page plein écran
# ════════════════════════════════════════════════════════════

@stats_bp.route('/classement')
def classement():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    current_user_name = session.get('user', '')
    players = []
    house_name = None
    house_id = None

    from app import (get_db_connection, now_paris, get_house_players_points)

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
                from datetime import date, timedelta
                today = now_paris().date()
                monday = (today - timedelta(days=today.weekday())).isoformat()
                thirty_days_ago = (today - timedelta(days=30)).isoformat()
                today_iso = today.isoformat()
                for p in players:
                    p['is_current_user'] = (p.get('email') == current_user_name)
                    p.setdefault('daily_points', 0)
                    p.setdefault('daily_tasks', 0)
                    p.setdefault('weekly_points', 0)
                    p.setdefault('weekly_tasks', 0)
                    p.setdefault('monthly_points', 0)
                    p.setdefault('monthly_tasks', 0)
                    email = p.get('email', '')
                    try:
                        # Daily
                        c.execute("SELECT COALESCE(SUM(points),0), COUNT(*) FROM completed_tasks WHERE user_email=? AND house_id=? AND CAST(completed_at AS TEXT) LIKE ?", (email, house_id, today_iso + '%'))
                        rd = c.fetchone()
                        p['daily_points'] = int(rd[0]) if rd and rd[0] else 0
                        p['daily_tasks'] = int(rd[1]) if rd and rd[1] else 0
                    except Exception:
                        pass
                    try:
                        # Weekly
                        c.execute("SELECT COALESCE(SUM(points),0), COUNT(*) FROM completed_tasks WHERE user_email=? AND house_id=? AND CAST(completed_at AS TEXT) >= ?", (email, house_id, monday))
                        rw = c.fetchone()
                        p['weekly_points'] = int(rw[0]) if rw and rw[0] else 0
                        p['weekly_tasks'] = int(rw[1]) if rw and rw[1] else 0
                    except Exception:
                        pass
                    try:
                        # Monthly (30 derniers jours)
                        c.execute("SELECT COALESCE(SUM(points),0), COUNT(*) FROM completed_tasks WHERE user_email=? AND house_id=? AND CAST(completed_at AS TEXT) >= ?", (email, house_id, thirty_days_ago))
                        rm = c.fetchone()
                        p['monthly_points'] = int(rm[0]) if rm and rm[0] else 0
                        p['monthly_tasks'] = int(rm[1]) if rm and rm[1] else 0
                    except Exception:
                        pass
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
# 📊 API — Stats hebdomadaires et mensuelles
# ════════════════════════════════════════════════════════════

@stats_bp.route('/api/weekly_tasks')
def api_weekly_tasks():
    """Retourne les tâches validées cette semaine par joueur (même format que daily_tasks)"""
    if 'user' not in session:
        return {'tasks': []}, 200
    from datetime import date, timedelta
    from app import (get_db_connection, now_paris, to_paris, _dbg)

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'tasks': []}, 200
        house_id = row[0]
        monday = (now_paris().date() - timedelta(days=now_paris().date().weekday())).isoformat()
        c.execute("""
            SELECT u.name, ct.task_name, ct.points, ct.category, ct.completed_at
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ? AND u.house_id = ?
              AND CAST(ct.completed_at AS TEXT) >= ?
            ORDER BY ct.completed_at DESC
        """, (house_id, house_id, monday))
        rows = c.fetchall()
        _jours_fr = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']
        tasks = []
        for name, task_name, points, category, done_at in rows:
            time_str = ''
            try:
                paris_dt = to_paris(done_at)
                if hasattr(paris_dt, 'strftime'):
                    jour = _jours_fr[paris_dt.weekday()]
                    time_str = jour + ' ' + paris_dt.strftime('%H:%M')
            except Exception:
                pass
            tasks.append({'player_name': name or '?', 'task_name': task_name, 'points': points or 0, 'time': time_str})
        return {'tasks': tasks}, 200
    except Exception as e:
        _dbg(f"Erreur API weekly_tasks: {e}")
        return {'tasks': [], 'error': str(e)}, 500
    finally:
        conn.close()


@stats_bp.route('/api/monthly_tasks')
def api_monthly_tasks():
    """Retourne les tâches validées ce mois par joueur (même format que daily_tasks)"""
    if 'user' not in session:
        return {'tasks': []}, 200
    from datetime import date, timedelta
    from app import (get_db_connection, now_paris, to_paris, _dbg)

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'tasks': []}, 200
        house_id = row[0]
        # 30 derniers jours pour que le mois ait toujours >= semaine
        thirty_days_ago = (now_paris().date() - timedelta(days=30)).isoformat()
        c.execute("""
            SELECT u.name, ct.task_name, ct.points, ct.category, ct.completed_at
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ? AND u.house_id = ?
              AND CAST(ct.completed_at AS TEXT) >= ?
            ORDER BY ct.completed_at DESC
        """, (house_id, house_id, thirty_days_ago))
        rows = c.fetchall()
        _jours_fr = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']
        tasks = []
        for name, task_name, points, category, done_at in rows:
            time_str = ''
            try:
                paris_dt = to_paris(done_at)
                if hasattr(paris_dt, 'strftime'):
                    jour = _jours_fr[paris_dt.weekday()]
                    time_str = jour + ' ' + paris_dt.strftime('%H:%M')
            except Exception:
                pass
            tasks.append({'player_name': name or '?', 'task_name': task_name, 'points': points or 0, 'time': time_str})
        return {'tasks': tasks}, 200
    except Exception as e:
        _dbg(f"Erreur API monthly_tasks: {e}")
        return {'tasks': [], 'error': str(e)}, 500
    finally:
        conn.close()


@stats_bp.route('/api/weekly_stats')
def api_weekly_stats():
    """
    API pour les stats hebdomadaires de tous les joueurs.
    Utilisé par le widget classement du bas dans menu.html
    """
    if 'user' not in session:
        return jsonify({'players': []}), 200

    from datetime import date, timedelta
    from app import (get_db_connection, now_paris, get_house_players_points, _dbg)

    conn = get_db_connection()
    c = conn.cursor()

    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return jsonify({'players': []}), 200

        house_id = row[0]

        # Lundi de la semaine en cours
        today = now_paris().date()
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
