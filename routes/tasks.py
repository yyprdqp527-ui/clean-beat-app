from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify, flash
import os
import sys
import threading

tasks_bp = Blueprint('tasks', __name__)

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

@tasks_bp.route('/categorie/<cat>')
def categorie(cat):
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
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


# Route pour ajouter ou modifier une tâche personnalisée (GET: formulaire, POST: traitement)
@tasks_bp.route('/add_task/<cat>', methods=['GET', 'POST'])
@tasks_bp.route('/edit_custom_task/<cat>/<int:task_id>', methods=['GET', 'POST'])
def add_task_page(cat, task_id=None):
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
    if 'user' not in session:
        flash("Connecte-toi pour créer une mission.", "warning")
        return redirect(url_for('auth.login'))

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
        return redirect(url_for('menu') + '?nav=1')
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
                return redirect(url_for('tasks.categorie', cat=cat))
        else:
            conn.close()
            flash("Mission introuvable.", "danger")
            return redirect(url_for('tasks.categorie', cat=cat))

    if request.method == 'POST':
        task_name = request.form.get('task_name', '').strip()
        task_description = request.form.get('task_description', '').strip()
        points = request.form.get('points', 10)
        try:
            points = int(points)
        except Exception:
            points = 10
        
        # Gestion de l'image - stockage base64 en DB (compatible Render filesystem éphémère)
        task_image_filename = None
        
        # Vérifier si un fichier a été uploadé
        if 'task_image' in request.files:
            file = request.files['task_image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Compresser et convertir en base64 data URI (pas de fichier sur disque)
                try:
                    from PIL import Image, ImageOps
                    import io as _io
                    img = Image.open(file)
                    img = ImageOps.exif_transpose(img)
                    img = img.convert('RGB')
                    img.thumbnail((800, 800), Image.LANCZOS)
                    buf = _io.BytesIO()
                    img.save(buf, format='JPEG', quality=80, optimize=True)
                    image_data = buf.getvalue()
                except ImportError:
                    image_data = file.read()
                import base64 as _b64
                compressed_b64 = _b64.b64encode(image_data).decode('utf-8')
                task_image_filename = f"data:image/jpeg;base64,{compressed_b64}"
        
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
                
                message_content = f"⭐ {creator_name} a ajouté une nouvelle mission : '{task_name}' dans {category_name} ({points} pts)"
                _house_id = house_id
                _msg = message_content
                _sender = session['user']
                _cat = normalized_cat
                def _notif():
                    try:
                        create_system_message(
                            _house_id, _msg, 'task_added',
                            sender_email=_sender,
                            related_category=_cat)
                    except Exception:
                        pass
                threading.Thread(
                    target=_notif, daemon=True).start()
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
        
        return redirect(url_for('tasks.categorie', cat=cat))

    conn.close()
    # Afficher le formulaire
    return render_template('add_custom_task.html', 
                           category=cat, 
                           category_name=category_name,
                           category_icon=category_icon,
                           task=existing_task,
                           hide_header=True)

# Mettre à jour les points d'une tâche prédéfinie (override par maison)
@tasks_bp.route('/update_task_points/<cat>/<int:task_id>', methods=['POST'])
def update_task_points(cat, task_id):
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
    if 'user' not in session:
        flash("Connecte-toi pour modifier les points.", "warning")
        return redirect(url_for('auth.login'))
    
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
        return redirect(url_for('house.invite_partner'))

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

    return redirect(url_for('tasks.categorie', cat=cat))

# Mettre à jour les points d'une tâche personnalisée
@tasks_bp.route('/update_custom_task_points/<cat>/<int:task_id>', methods=['POST'])
def update_custom_task_points(cat, task_id):
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
    if 'user' not in session:
        flash("Connecte-toi pour modifier les points.", "warning")
        return redirect(url_for('auth.login'))
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
        return redirect(url_for('house.invite_partner'))
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
    return redirect(url_for('tasks.categorie', cat=cat))

@tasks_bp.route('/task_page/<cat>/<int:task_id>')
def task_page(cat, task_id):
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
    # Affiche une page simple ou un message temporaire
    return f"Page de la tâche {task_id} pour la catégorie : {cat} (à implémenter)"

@tasks_bp.route('/custom_task_page/<int:task_id>', methods=['GET', 'POST'])
def custom_task_page(task_id):
    """
    Page de validation pour les tâches personnalisées (créées par les utilisateurs)
    Similaire à task_enhanced mais pour les custom_tasks
    """
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
    if 'user' not in session:
        flash("Connecte-toi pour accéder à cette tâche.", "warning")
        return redirect(url_for('auth.signup_email'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la tâche personnalisée (colonnes: task_name, task_description, task_image)
    c.execute("SELECT id, task_name, task_description, points, category, task_image, created_by, house_id FROM custom_tasks WHERE id=?", (task_id,))
    row = c.fetchone()
    
    if not row:
        flash("Tâche personnalisée introuvable.", "warning")
        conn.close()
        return redirect(url_for('menu') + '?nav=1')
    
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
        return redirect(url_for('menu') + '?nav=1')
    
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
        today = now_paris().date().isoformat()
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
        today = now_paris().date().isoformat()
        
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
                return redirect(url_for('menu') + '?nav=1')
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
                return redirect(url_for('menu') + '?nav=1')
        
        # Récupérer le joueur qui a fait la tâche (depuis le formulaire)
        _raw_pe = request.form.get('player_email', '')
        player_email = _raw_pe if _raw_pe else session['user']
        
        # Vérifier que ce joueur est bien dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (player_email,))
        player_row = c.fetchone()
        if not player_row or player_row[0] != user_house_id:
            flash("Erreur : joueur invalide", "danger")
            conn.close()
            return redirect(url_for('menu') + '?nav=1')
        
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
            
            # 🎯 Message automatique à la validation de tâche
            try:
                message_content = f"✅ {player_name} a validé '{task_name}' (+{task_points} pts)"
                create_system_message(user_house_id, message_content, 'task_completed')
                
                # 💬 Envoyer un message de félicitation si le joueur a fait 3 tâches ou plus aujourd'hui
                try:
                    today = date.today().isoformat()
                    c_check = conn.cursor()
                    c_check.execute("""
                        SELECT COUNT(*) FROM completed_tasks 
                        WHERE user_email=? AND DATE(completed_at)=?
                    """, (player_email, today))
                    task_count = c_check.fetchone()[0]
                    
                    if task_count >= 3 and task_count % 3 == 0:  # À chaque multiple de 3
                        congrats_msg = (
                            f"🏆 {player_name} a validé "
                            f"'{task_name}' et gagne "
                            f"{task_points} points !"
                        )
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


@tasks_bp.route('/task_enhanced/<cat>/<int:task_id>', methods=['GET', 'POST'])
def task_enhanced(cat, task_id):
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
    # Normaliser le nom de la catégorie
    normalized_cat = normalize_category(cat)
    
    # Affiche la page 'enhanced' d'une tâche et permet de la valider (POST)
    if normalized_cat not in TASKS_CONFIG or task_id < 0 or task_id >= len(TASKS_CONFIG.get(normalized_cat, [])):
        # Si tâche non définie, afficher message simple
        flash("Tâche introuvable.", "warning")
        return redirect(url_for('tasks.categorie', cat=cat))

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
            today = now_paris().date().isoformat()
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
            return redirect(url_for('auth.signup_email'))

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
            return redirect(url_for('menu') + '?nav=1')
        
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
        today = now_paris().date().isoformat()
        
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
                return redirect(url_for('menu') + '?nav=1')
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
                return redirect(url_for('menu') + '?nav=1')

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
@tasks_bp.route('/debug_task_id/<cat>/<int:tid>')
def debug_task_id(cat, tid):
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
    return f"<html><body><h1>DEBUG</h1><p>cat={cat}, tid={tid}</p><script>var taskId = {tid}; console.log('taskId:', taskId);</script></body></html>"


# � API : Valider une tâche en AJAX (pour permettre le son automatique)
@tasks_bp.route('/api/validate_task', methods=['POST'])
def api_validate_task():
    """
    Valide une tâche via AJAX sans rechargement de page.
    Retourne les infos nécessaires pour jouer le son et afficher l'animation.
    """
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
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
            # Vérifier si la maison a personnalisé les points pour cette tâche
            try:
                c.execute("SELECT points FROM task_points_overrides WHERE house_id=? AND category=? AND task_index=?",
                          (user_house_id, normalized_cat, int(task_id)))
                _ov = c.fetchone()
                if _ov and _ov[0] is not None:
                    task_points = int(_ov[0])
            except Exception:
                pass
            # Utiliser le nom du payload, sinon celui de TASKS_CONFIG
            task_name = task_name_from_payload if task_name_from_payload else task.get('name')
        
        _dbg(f"   📌 FINAL task_name = '{task_name}'")
        _dbg(f"📋 [END DEBUG]\n")
        
        today = now_paris().date().isoformat()
        
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
        
        # 🏠 Missions custom : vérifier si un AUTRE joueur de la maison l'a déjà validée aujourd'hui
        if task_type == 'custom':
            c.execute("""SELECT u.name FROM completed_tasks ct
                         JOIN users u ON u.email = ct.user_email
                         WHERE ct.house_id=? AND ct.category=? AND ct.task_name=?
                         AND DATE(ct.completed_at)=? AND ct.user_email != ?""",
                     (user_house_id, category, task_name, today, player_email))
            other = c.fetchone()
            if other:
                other_name = other[0] or 'Un coéquipier'
                return jsonify({
                    'success': False,
                    'error': 'already_done_by_other',
                    'message': f"{other_name} a déjà validé cette mission aujourd'hui ! Gardez-la pour un autre jour ou supprimez-la. 😊",
                    'player_name': other_name
                }), 200

        # Insérer la tâche complétée
        c.execute("INSERT INTO completed_tasks (user_email, house_id, category, task_name, points, completed_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                 (player_email, user_house_id, category, task_name, task_points))
        c.execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE email=?", (task_points, player_email))

        # ✅ COMMIT IMMÉDIAT — sécuriser l'INSERT + UPDATE avant toute opération optionnelle
        # Sur PostgreSQL, si une requête échoue après, le rollback auto annulerait l'INSERT
        conn.commit()

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
                    """, (user_house_id, player_email, message_text, now_paris().isoformat()))
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
        
        # ✅ Marquer les messages task_added de CETTE catégorie non lus comme lus pour ce joueur
        # (il a validé une mission de cette pièce → seul le rappel de cette pièce s'éteint)
        try:
            _cat_to_mark = normalize_category(category) if category else None
            if _cat_to_mark:
                c.execute("""
                    SELECT m.id FROM messages m
                    WHERE m.house_id = ? AND m.message_type = 'task_added'
                    AND m.related_category = ?
                    AND NOT EXISTS (
                        SELECT 1 FROM message_reads mr
                        WHERE mr.message_id = m.id AND mr.user_email = ?
                    )
                """, (user_house_id, _cat_to_mark, player_email))
                for msg_row in c.fetchall():
                    c.execute("""
                        INSERT INTO message_reads (message_id, user_email)
                        VALUES (?, ?) ON CONFLICT(message_id, user_email) DO NOTHING
                    """, (msg_row[0], player_email))
        except Exception:
            pass

        # ✅ Commit des opérations optionnelles (badges, santé, baby tracking)
        try:
            conn.commit()
        except Exception:
            pass
        
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
                
                # 🟠 Notifier tous les joueurs que la mission a été validée
                # → déclenche refreshMissionDots() + refreshAllBadges() côté client
                safe_socketio_emit('task_validated', {
                    'category': category,
                    'task_name': task_name,
                    'player_email': player_email
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


# 🎯 NOUVELLE ROUTE API : Récupérer les tâches validées aujourd'hui
@tasks_bp.route('/api/daily_tasks')
def api_daily_tasks():
    """
    Retourne les tâches validées aujourd'hui avec heure, joueur, points
    Format JSON pour affichage dans le dashboard
    """
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
    if 'user' not in session:
        return {'tasks': []}, 200
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'tasks': []}, 200
        
        house_id = row[0]
        today = now_paris().date().isoformat()

        c.execute("""
            SELECT u.name, ct.task_name, ct.points, ct.category,
                   ct.completed_at as done_at, ct.user_email, ct.id
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ? AND u.house_id = ?
              AND CAST(ct.completed_at AS TEXT) LIKE ?
              AND (ct.category IS NULL OR ct.category NOT IN ('bonus', 'malus'))
            ORDER BY ct.completed_at DESC
        """, (house_id, house_id, today + '%'))
        
        rows = c.fetchall()
        _jours_fr = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']
        tasks = []
        for name, task_name, points, category, done_at, user_email, task_id in rows:
            time_str = ''
            try:
                paris_dt = to_paris(done_at)
                if hasattr(paris_dt, 'strftime'):
                    jour = _jours_fr[paris_dt.weekday()]
                    time_str = jour + ' ' + paris_dt.strftime('%H:%M')
                elif paris_dt and ' ' in str(paris_dt):
                    time_str = str(paris_dt).split(' ')[1][:5]
            except Exception:
                pass
            tasks.append({
                'player_name': name or '?',
                'player_email': user_email or '',
                'task_name': task_name,
                'points': points or 0,
                'time': time_str,
                'task_id': task_id or 0,
                'is_current_user': (user_email == session.get('user', '')),
            })
        return {'tasks': tasks}, 200
        
    except Exception as e:
        _dbg(f"Erreur API daily_tasks: {e}")
        return {'tasks': [], 'error': str(e)}, 500
    finally:
        conn.close()



@tasks_bp.route('/api/rooms_with_missions')
def api_rooms_with_missions():
    """
    API pour récupérer les pièces avec missions non validées.
    Utilisé pour mettre à jour les pastilles oranges en temps réel.
    """
    from app import get_db_connection, normalize_category, get_house_players_points, get_house_players_with_colors, get_house_push_subscriptions, create_system_message, safe_socketio_emit, _dbg, TASKS_CONFIG, allowed_file, get_user_points, mark_message_as_read, now_paris, to_paris, SOCKETIO_AVAILABLE, socketio
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
                AND ctd.task_name = ct.task_name
                AND ctd.completed_at >= ct.created_at
            )
            GROUP BY ct.category
        """, (house_id,))
        rooms = {row[0]: row[1] for row in c.fetchall()}
        conn.close()
        return jsonify({'rooms': rooms})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
