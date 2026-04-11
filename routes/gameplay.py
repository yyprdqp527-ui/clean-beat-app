from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify
from datetime import timedelta

gameplay_bp = Blueprint('gameplay_bp', __name__)


# ════════════════════════════════════════════════════════════
# 🎮 GAMEPLAY — Page de fonctionnalités de jeu (malus/bonus)
# ════════════════════════════════════════════════════════════
@gameplay_bp.route('/gameplay')
def gameplay():
    from app import get_db_connection, get_house_players_points, _dbg
    if 'user' not in session:
        return redirect(url_for('auth.login'))
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
# 🎓 ONBOARDING — Marquer comme vu
# ════════════════════════════════════════════════════════════
@gameplay_bp.route('/api/mark_onboarding_seen', methods=['POST'])
def api_mark_onboarding_seen():
    from app import get_db_connection
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
@gameplay_bp.route('/api/send_malus', methods=['POST'])
def api_send_malus():
    from app import get_db_connection, now_paris, _dbg
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
        c.execute("""
            SELECT COUNT(*) FROM completed_tasks
            WHERE user_email=? AND category='malus'
            AND task_name LIKE ? AND DATE(completed_at)=DATE('now')
        """, (target_email, '%' + sender_name + '%'))
        count_today = c.fetchone()[0]
        if count_today >= 3:
            return jsonify({'success': False, 'error': f'Tu as déjà envoyé 3 malus à {target_name} aujourd\'hui !'}), 200

        # Max 1 sanction (bonus/malus/suspicion) par heure vers la même cible
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

        # Insérer le malus comme tâche avec points négatifs
        task_context = str(data.get('task', '')).strip()[:100]
        task_name = f'Malus de {sender_name} : {reason_label}'
        if task_context:
            task_name += f' | {task_context}'
        c.execute("""
            INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
            VALUES (?, ?, 'malus', ?, ?, CURRENT_TIMESTAMP)
        """, (target_email, task_name, points, house_id))
        # Badge 💀 sur l'avatar de la cible pendant 1 heure
        skull_until = (now_paris() + timedelta(hours=1)).isoformat()
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


@gameplay_bp.route('/api/send_bonus', methods=['POST'])
def api_send_bonus():
    from app import get_db_connection, now_paris, _dbg
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

        task_context = str(data.get('task', '')).strip()[:100]
        task_name = f'Bonus de {sender_name} : {reason_label}'
        if task_context:
            task_name += f' | {task_context}'
        c.execute("""
            INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
            VALUES (?, ?, 'bonus', ?, ?, CURRENT_TIMESTAMP)
        """, (target_email, task_name, points, house_id))
        # Badge ❤️ sur l'avatar de la cible pendant 1 heure
        bonus_until = (now_paris() + timedelta(hours=1)).isoformat()
        c.execute("UPDATE users SET bonus_expires_at=? WHERE email=?", (bonus_until, target_email))
        conn.commit()

        from datetime import date as _d
        today = _d.today().isoformat()
        c.execute("""
            SELECT COALESCE(SUM(points), 0) FROM completed_tasks
            WHERE user_email=? AND house_id=? AND DATE(completed_at)=?
        """, (target_email, house_id, today))
        new_total = int(c.fetchone()[0] or 0)

        return jsonify({'success': True, 'new_total': new_total, 'message': f'❤️ Bonus envoyé à {target_name} ! (+{points} pts)'})
    except Exception as e:
        conn.rollback()
        _dbg(f"ERREUR api_send_bonus: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════
# 🎡 API ROUE DE LA CHANCE — Tâches impopulaires bonus
# ════════════════════════════════════════════════════════════
@gameplay_bp.route('/api/spin_wheel', methods=['POST'])
def api_spin_wheel():
    """
    Ajoute une tâche obtenue via la roue de la chance.
    La tâche est ajoutée comme custom_task pour le joueur courant.
    """
    from app import get_db_connection, _dbg
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


@gameplay_bp.route('/api/complete_wheel_task', methods=['POST'])
def api_complete_wheel_task():
    """Valide une corvée obtenue via la roue et ajoute les points au joueur."""
    from app import get_db_connection, _dbg
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

@gameplay_bp.route('/api/give_malus', methods=['POST'])
def api_give_malus():
    """
    Donne un malus à un joueur : retire des points ET ajoute un skull pendant 24h.
    """
    from app import get_db_connection, now_paris, _dbg
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
        today = now_paris().date().isoformat()
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
        malus_task_name = f'Malus de {sender_name}' + (f' : {task_name}' if task_name else '')
        c.execute("""
            INSERT INTO completed_tasks (user_email, task_name, category, points, house_id, completed_at)
            VALUES (?, ?, 'malus', ?, ?, CURRENT_TIMESTAMP)
        """, (target_email, malus_task_name, points, house_id))

        # 💀 SKULL : Ajouter un skull pendant 1h
        skull_expires = (now_paris() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
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


@gameplay_bp.route('/api/active_malus', methods=['GET'])
def api_active_malus():
    """
    Renvoie la liste des joueurs qui ont un skull actif
    = ayant reçu un malus dans les 60 dernières minutes.
    Basé sur completed_tasks (robuste, pas besoin de skull_expires_at).
    """
    from app import get_db_connection, _dbg
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

        # Joueurs ayant reçu un malus dans la dernière heure
        c.execute("""
            SELECT ct.user_email, u.name, ct.task_name
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ?
              AND ct.category = 'malus'
              AND ct.completed_at >= datetime('now', '-1 hour')
            ORDER BY ct.completed_at DESC
        """, (house_id,))

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


@gameplay_bp.route('/api/active_bonus', methods=['GET'])
def api_active_bonus():
    """
    Renvoie la liste des joueurs qui ont reçu un bonus dans la dernière heure.
    Miroir de api_active_malus mais pour la catégorie 'bonus'.
    """
    from app import get_db_connection, _dbg
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

        c.execute("""
            SELECT ct.user_email, u.name, ct.task_name
            FROM completed_tasks ct
            INNER JOIN users u ON ct.user_email = u.email
            WHERE ct.house_id = ?
              AND ct.category = 'bonus'
              AND ct.completed_at >= datetime('now', '-1 hour')
            ORDER BY ct.completed_at DESC
        """, (house_id,))

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


@gameplay_bp.route('/api/house_suspicions', methods=['GET'])
def api_house_suspicions():
    """
    Renvoie TOUTES les suspicions de la maison (publique, visible par tous).
    Similaire à api_active_malus mais pour les suspicions.
    """
    from app import get_db_connection, _dbg
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
            
            photo_p = row[8]
            photo_url = ('/' + photo_p) if photo_p else None
            suspicions.append({
                'id': row[0],
                'suspecting_email': row[1],
                'suspecting_name': row[2],
                'suspected_email': row[3],
                'suspected_name': row[4],
                'task_name': row[5],
                'task_points': row[6],
                'status': row[7],
                'photo_path': photo_p,
                'photo_url': photo_url,
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


@gameplay_bp.route('/api/active_suspicions', methods=['GET'])
def api_active_suspicions():
    """
    Renvoie la liste des joueurs qui ont une suspicion active (pending ou awaiting_validation).
    Utilisé pour afficher la loupe 🔍 sur les avatars.
    """
    from app import get_db_connection, _dbg
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


@gameplay_bp.route('/api/proof/tasks')
def api_proof_tasks():
    """Tâches récentes des colocataires (dernières 24h) qu'on peut contester."""
    from app import get_db_connection, _dbg
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



@gameplay_bp.route('/api/proof/all')
def api_proof_all():
    """Vue unifiée : toutes les tâches du jour avec statut contestation pour TOUS les joueurs."""
    from app import get_db_connection, _dbg
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

@gameplay_bp.route('/api/proof/request', methods=['POST'])
def api_proof_request():
    """Demander une preuve photo : coûte 3 pts au demandeur."""
    from app import get_db_connection, _dbg
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


@gameplay_bp.route('/api/proof/submit', methods=['POST'])
def api_proof_submit():
    """Soumettre une photo comme preuve. Le demandeur pourra ensuite valider ou réfuter."""
    from app import get_db_connection, save_photo_from_base64, _dbg
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
    # Compresser la photo base64 (max 800×800, JPEG q75)
    compressed = save_photo_from_base64(photo_data)
    if compressed:
        photo_data = compressed
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


@gameplay_bp.route('/api/proof/validate', methods=['POST'])
def api_proof_validate():
    """
    Valider (preuve ok) ou réfuter (tricherie) une preuve soumise.
    verdict = 'validated' : accusateur perd 10 pts, accusé gagne task_points en bonus
    verdict = 'refuted'   : accusateur gagne 10 pts, accusé perd 10 pts + skull 24h
    """
    from app import get_db_connection, now_paris, _dbg
    from datetime import datetime
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
            skull_expires = (now_paris() + timedelta(hours=24)).isoformat()
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


@gameplay_bp.route('/api/proof/pending')
def api_proof_pending():
    """Preuves soumises en attente de jugement (pour le demandeur) + demandes envoyées à moi."""
    from app import get_db_connection, _dbg
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
