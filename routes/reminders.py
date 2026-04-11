from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify, flash

reminders_bp = Blueprint('reminders', __name__)


# ========================================
# Routes pour les rappels personnels (mini agenda / to-do list)
# ========================================

@reminders_bp.route('/reminders')
def reminders():
    """Page des rappels personnels du joueur (mini agenda)"""
    from app import get_db_connection, mark_message_as_read, _dbg
    if 'user' not in session:
        flash("Connecte-toi pour accéder à tes rappels", "warning")
        return redirect(url_for('auth.login'))

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
    # Actifs (non cochés) en premier, plus récents en haut ; puis cochés en bas
    c.execute("""
        SELECT pr.id, pr.title, pr.remind_at, pr.is_done, pr.created_at, pr.user_email, 
               u.name, u.avatar, u.avatar_file, u.avatar_url
        FROM player_reminders pr
        LEFT JOIN users u ON pr.user_email = u.email
        WHERE pr.house_id=?
        ORDER BY pr.is_done ASC, pr.created_at DESC
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


@reminders_bp.route('/reminders/add', methods=['POST'])
def add_reminder():
    """Ajouter un rappel personnel"""
    from app import get_db_connection, _dbg, safe_socketio_emit, create_system_message
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

    # Reset auto : si 30 articles barrés, supprimer tous les articles cochés
    c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=1", (house_id,))
    done_count = c.fetchone()[0] or 0
    if done_count >= 30:
        c.execute("DELETE FROM player_reminders WHERE house_id=? AND is_done=1", (house_id,))

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
            'pending_count': _courses_pending,
            'creator_name': creator_name,
            'creator_avatar': creator_avatar,
            'creator_avatar_file': creator_avatar_file,
            'creator_avatar_url': creator_avatar_url
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


@reminders_bp.route('/reminders/toggle/<int:reminder_id>', methods=['POST'])
def toggle_reminder(reminder_id):
    """Cocher / décocher un article de la liste de courses (+1 pt quand on coche)"""
    from app import get_db_connection, _dbg, safe_socketio_emit, mark_message_as_read
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
    c.execute("SELECT is_done, title FROM player_reminders WHERE id=? AND house_id=?",
              (reminder_id, user_house))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Article introuvable'})

    item_title = row[1] or 'Article'
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
                      (session['user'], house_id, 'courses', item_title, 1))
            points_earned = 1

    conn.commit()

    # Si l'article vient d'être coché, vérifier si TOUTE la liste est faite
    # → marquer tous les courses_added non lus comme lus pour cet utilisateur
    if new_done == 1:
        try:
            c.execute(
                "SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0",
                (user_house,)
            )
            remaining = c.fetchone()[0]
            if remaining == 0:
                # Toute la liste est cochée → éteindre la pill courses pour cet utilisateur
                c.execute("""
                    SELECT m.id FROM messages m
                    WHERE m.house_id = ? AND m.message_type = 'courses_added'
                    AND NOT EXISTS (
                        SELECT 1 FROM message_reads mr
                        WHERE mr.message_id = m.id AND mr.user_email = ?
                    )
                """, (user_house, session['user']))
                for msg_row in c.fetchall():
                    c.execute("""
                        INSERT INTO message_reads (message_id, user_email)
                        VALUES (?, ?) ON CONFLICT(message_id, user_email) DO NOTHING
                    """, (msg_row[0], session['user']))
                conn.commit()
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
        c.execute("SELECT name FROM users WHERE email=?", (session['user'],))
        pn = c.fetchone()
        player_name_resp = pn[0] if pn else session['user'].split('@')[0]
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


@reminders_bp.route('/reminders/delete/<int:reminder_id>', methods=['POST'])
def delete_reminder(reminder_id):
    """Supprimer un rappel"""
    from app import get_db_connection, safe_socketio_emit
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

    # Compter les articles restants non cochés pour la pastille
    _pending_after_delete = 0
    if hr and hr[0]:
        try:
            c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (hr[0],))
            _pending_after_delete = c.fetchone()[0] or 0
        except Exception:
            pass

    conn.close()

    # Synchroniser la suppression pour tous les joueurs
    if hr and hr[0]:
        try:
            safe_socketio_emit('reminder_deleted', {
                'id': reminder_id,
                'pending_count': _pending_after_delete
            }, namespace='/', room=f'house_{hr[0]}', broadcast=True)
        except Exception:
            pass

    return jsonify({'success': True})


# 💬 ========== ROUTES API RAPPELS ==========

@reminders_bp.route('/api/reminders/settings', methods=['GET'])
def api_get_reminder_settings():
    """
    Récupère les paramètres de rappels de l'utilisateur.
    """
    from app import get_user_reminder_settings
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401

    settings = get_user_reminder_settings(session['user'])
    return {'success': True, 'settings': settings}, 200


@reminders_bp.route('/api/reminders/settings', methods=['POST'])
def api_update_reminder_settings():
    """
    Met à jour les paramètres de rappels de l'utilisateur.
    """
    from app import update_user_reminder_settings
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


@reminders_bp.route('/api/reminders/test', methods=['POST'])
def api_test_reminder():
    """
    Envoie un rappel de test immédiat.
    """
    from app import get_db_connection, _dbg, create_reminder, send_reminder
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
