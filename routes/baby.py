from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify

baby_bp = Blueprint('baby', __name__)


# 👶 ========== ROUTES SUIVI BÉBÉ ==========

@baby_bp.route('/baby_tracking/<cat>/<int:task_id>')
def baby_tracking(cat, task_id):
    """Page de suivi pour les tâches de bébé (biberon, couches, sommeil)"""
    from app import get_db_connection, normalize_category, TASKS_CONFIG, _dbg
    _dbg(f"👶 PAGE BABY_TRACKING accédée par {session.get('user', 'NON_CONNECTE')} pour task_id={task_id}")

    if 'user' not in session:
        flash("Connecte-toi pour utiliser le suivi bébé.", "warning")
        return redirect(url_for('auth.login'))

    normalized_cat = normalize_category(cat)

    if normalized_cat not in TASKS_CONFIG or task_id < 0 or task_id >= len(TASKS_CONFIG.get(normalized_cat, [])):
        flash("Tâche introuvable.", "warning")
        return redirect(url_for('tasks.categorie', cat=cat))

    task = TASKS_CONFIG[normalized_cat][task_id]
    task_name = task.get('name')

    task_type = None
    if 'biberon' in task_name.lower():
        task_type = 'biberon'
    elif 'couche' in task_name.lower():
        task_type = 'couches'
    elif 'dormir' in task_name.lower() or 'sommeil' in task_name.lower():
        task_type = 'sommeil'

    if not task_type:
        flash("Cette tâche ne nécessite pas de suivi spécial.", "info")
        return redirect(url_for('tasks.task_enhanced', cat=cat, task_id=task_id))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    house_id = row[0] if row else None

    history = []
    if house_id:
        c.execute("""
            SELECT bt.user_email, bt.tracking_time, bt.bottle_ml, bt.observations,
                   datetime(bt.created_at, 'localtime') as created_at,
                   u.avatar_url, u.avatar_file, u.avatar
            FROM baby_tracking bt
            LEFT JOIN users u ON bt.user_email = u.email
            WHERE bt.house_id=? AND bt.task_type=?
            ORDER BY bt.created_at DESC
            LIMIT 5
        """, (house_id, task_type))
        history = [dict(zip(['user_email', 'tracking_time', 'bottle_ml', 'observations', 'created_at', 'avatar_url', 'avatar_file', 'avatar'], row))
                   for row in c.fetchall()]

    conn.close()

    # Marquer tous les messages baby_tracking comme lus pour cet utilisateur
    if house_id:
        try:
            from app import get_db_connection, safe_socketio_emit
            conn_mark = get_db_connection()
            c_mark = conn_mark.cursor()
            c_mark.execute("""
                INSERT OR IGNORE INTO message_reads (message_id, user_email)
                SELECT m.id, ?
                FROM messages m
                WHERE m.house_id = ?
                AND m.message_type = 'baby_tracking'
                AND NOT EXISTS (
                    SELECT 1 FROM message_reads mr
                    WHERE mr.message_id = m.id AND mr.user_email = ?
                )
            """, (session['user'], house_id, session['user']))
            conn_mark.commit()
            conn_mark.close()
            safe_socketio_emit('baby_badge_update', {
                'count': 0,
                'user_email': session['user']
            }, namespace='/', room=f'house_{house_id}', broadcast=True)
        except Exception as e:
            pass

    return render_template('baby_tracking.html',
                           task_name=task_name,
                           task_type=task_type,
                           category=cat,
                           task_id=task_id,
                           history=history)


@baby_bp.route('/save_baby_tracking', methods=['POST'])
def save_baby_tracking():
    """Enregistre un suivi de tâche bébé et envoie un message au partenaire"""
    from app import get_db_connection, now_paris, mark_message_as_read, SOCKETIO_AVAILABLE, socketio, safe_socketio_emit, _dbg
    _dbg(f"🍼 SAVE_BABY_TRACKING appelé par {session.get('user', 'INCONNU')}")

    if 'user' not in session:
        flash("Connecte-toi pour utiliser le suivi bébé.", "warning")
        return redirect(url_for('auth.login'))

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

    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    house_id = row[0] if row else None

    if not house_id:
        flash("Erreur : maison introuvable.", "danger")
        conn.close()
        return redirect(url_for('menu') + '?nav=1')

    c.execute("""
        INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session['user'], house_id, task_type, tracking_time, bottle_ml, observations))

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
    else:
        message_text = f"😴 {user_name} a couché bébé à {tracking_time}"
        if observations:
            message_text += f"\n📝 {observations}"

    conn.commit()
    conn.close()

    try:
        from app import create_system_message
        import threading
        if task_type == 'biberon':
            _push_title = '🍼 Biberon donné !'
        elif task_type == 'couches':
            _push_title = '👶 Change de couche !'
        elif task_type == 'sommeil':
            _push_title = '😴 Bébé dort !'
        else:
            _push_title = '👶 Suivi bébé'
        # ✅ Appel SYNCHRONE : message inséré en base AVANT le redirect
        # (thread daemon non fiable sur Gunicorn/Render — message jamais créé)
        create_system_message(
            house_id, message_text,
            'baby_tracking',
            sender_email=session['user'],
            push_title=_push_title)
    except Exception as e:
        _dbg(f"❌ Erreur create_system_message baby: {e}")

    # 🔌 WebSocket : notifier tous les joueurs en temps réel (pastille apparaît pour le partenaire)
    try:
        safe_socketio_emit('baby_tracking_added', {
            'house_id': house_id,
            'sender_email': session['user'],
            'message': message_text
        }, namespace='/', room=f'house_{house_id}', broadcast=True)
    except Exception as e:
        _dbg(f"⚠️ WebSocket baby_tracking_added: {e}")

    redirect_url = url_for('tasks.task_enhanced', cat=category, task_id=task_id)

    # 📡 Réponse AJAX (optimistic update côté client)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (request.headers.get('Accept') or ''):
        return jsonify({'success': True, 'redirect': redirect_url, 'message': message_text})

    flash(f"✅ Suivi enregistré et partagé avec votre partenaire !", "success")
    return redirect(redirect_url)
