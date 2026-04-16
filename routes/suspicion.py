import os
from flask import Blueprint, request, session, jsonify
from werkzeug.utils import secure_filename

suspicion_bp = Blueprint('suspicion', __name__)


@suspicion_bp.route('/api/emit_suspicion', methods=['POST'])
def api_emit_suspicion():
    """
    Émettre une suspicion sur une tâche complétée par un autre joueur.
    Coût potentiel : 10 points si la suspicion est infondée
    """
    from app import get_db_connection, _dbg, now_paris
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

        # 🔌 WebSocket: notifier la maison de la nouvelle suspicion
        try:
            from app import safe_socketio_emit, SOCKETIO_AVAILABLE, socketio
            if SOCKETIO_AVAILABLE and socketio:
                safe_socketio_emit('suspicion_update', {
                    'house_id': house_id,
                    'suspected': suspected_email,
                    'by': suspecting_email
                }, namespace='/', room=f'house_{house_id}', broadcast=True)
        except Exception:
            pass

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


@suspicion_bp.route('/api/upload_proof', methods=['POST'])
def api_upload_proof():
    """
    Le joueur soupçonné upload une photo de preuve
    """
    from app import get_db_connection, _dbg, now_paris
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
        timestamp = now_paris().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"proof_{suspicion_id}_{timestamp}_{filename}"

        # Créer le dossier uploads/proofs s'il n'existe pas
        from flask import current_app
        proofs_dir = os.path.join(current_app.root_path, 'uploads', 'proofs')
        os.makedirs(proofs_dir, exist_ok=True)

        # Compresser la photo avant sauvegarde (max 1200×1200, JPEG q80)
        try:
            from PIL import Image, ImageOps
            import io as _io
            img = Image.open(photo_file)
            img = ImageOps.exif_transpose(img)
            img = img.convert('RGB')
            img.thumbnail((1200, 1200), Image.LANCZOS)
            unique_filename = os.path.splitext(unique_filename)[0] + '.jpg'
            photo_path = os.path.join(proofs_dir, unique_filename)
            img.save(photo_path, format='JPEG', quality=80, optimize=True)
        except ImportError:
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


@suspicion_bp.route('/api/validate_proof', methods=['POST'])
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
    from app import get_db_connection, _dbg
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


@suspicion_bp.route('/api/my_suspicions', methods=['GET'])
def api_my_suspicions():
    """
    Récupère les suspicions impliquant l'utilisateur connecté
    (comme soupçonneux ou comme soupçonné)
    """
    from app import get_db_connection, _dbg
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
