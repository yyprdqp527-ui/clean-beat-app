from flask import Blueprint, request, session, redirect, url_for, render_template, flash

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
        return redirect(url_for('menu'))

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
        create_system_message(
            house_id,
            message_text,
            'baby_tracking',
            sender_email=session['user']
        )
    except Exception as e:
        _dbg(f"❌ Erreur create_system_message baby: {e}")

    flash(f"✅ Suivi enregistré et partagé avec votre partenaire !", "success")

    return redirect(url_for('tasks.task_enhanced', cat=category, task_id=task_id))
