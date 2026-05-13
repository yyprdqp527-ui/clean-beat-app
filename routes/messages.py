from flask import (
    Blueprint, session, request, flash,
    redirect, url_for, jsonify,
    render_template
)

messages_bp = Blueprint('messages', __name__)


@messages_bp.route('/comments', methods=['GET', 'POST'])
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
    from app import (get_db_connection, now_paris, _dbg, safe_socketio_emit,
                     create_system_message, mark_message_as_read,
                     get_unread_message_count, get_children_unread_counts,
                     get_unread_messages_by_sender, get_unread_count_by_type,
                     get_unread_messages_sent_to, get_house_players_with_colors,
                     to_paris, validate_avatar_file,
                     get_user_push_subscriptions, send_push_notification,
                     get_house_players_points, compute_user_total_badge)
    if 'user' not in session:
        flash("Connecte-toi pour accéder à la messagerie", "warning")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        flash("Tu dois rejoindre une maison pour accéder à la messagerie", "warning")
        return redirect(url_for('menu') + '?nav=1')
    
    house_id = user_row[0]
    current_user_name = user_row[1] if user_row[1] else session['user'].split('@')[0]

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        recipient_email = request.form.get('recipient', '').strip()
        
        if content and recipient_email:
            # Vérifier que le destinataire existe et est dans la même maison
            c.execute("SELECT email, name FROM users WHERE email=? AND house_id=?", (recipient_email, house_id))
            recipient = c.fetchone()
            
            if recipient:
                # Insérer le message
                timestamp = now_paris().isoformat()
                c.execute("""
                    INSERT INTO messages (house_id, sender_email, recipient_email, content, timestamp, sender_type, message_type)
                    VALUES (?, ?, ?, ?, ?, 'user', 'private')
                """, (house_id, session['user'], recipient_email, content, timestamp))
                message_id = c.lastrowid
                conn.commit()
                
                _dbg(f"💬 Message envoyé: {session['user']} → {recipient_email}: {content[:50]}")
                
                # Vérifier si le destinataire est un enfant + récupérer son nom
                c.execute("SELECT COALESCE(is_child_account, 0), name FROM users WHERE email=?", 
                         (recipient_email,))
                recipient_data = c.fetchone()
                is_recipient_child = recipient_data and recipient_data[0] == 1
                recipient_display_name = recipient_data[1] if recipient_data and recipient_data[1] else recipient_email.split('@')[0]

                # Avatar de l'expéditeur (pour insertion DOM côté client sans rechargement)
                c.execute("SELECT avatar, avatar_file, avatar_url FROM users WHERE email=?", (session['user'],))
                sender_av = c.fetchone()
                if sender_av:
                    if sender_av[1]:
                        sender_avatar = f"/static/avatars/{sender_av[1]}"
                    elif sender_av[2]:
                        sender_avatar = sender_av[2]
                    else:
                        sender_avatar = sender_av[0] or '👤'
                else:
                    sender_avatar = '👤'

                # ✅ Compteurs simplifiés
                recipient_unread_count = get_unread_message_count(recipient_email, house_id)
                children_unread = get_children_unread_counts(house_id)

                # ✅ Émettre l'événement WebSocket — payload enrichi pour insertion DOM directe
                safe_socketio_emit('new_message_notification', {
                    'message_id': message_id,
                    'sender': current_user_name,
                    'sender_email': session['user'],
                    'sender_avatar': sender_avatar,
                    'content': content,  # contenu COMPLET (le menu n'utilise pas ce champ pour le badge)
                    'timestamp': timestamp,
                    'recipient_email': recipient_email,
                    'recipient_name': recipient_display_name,
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
                        # Badge unifié via helper (même formule que notify_house_members)
                        total_badge = compute_user_total_badge(recipient_email, house_id)
                        notification_data = {
                            'title': f'💬 Message de {current_user_name}',
                            'body': content[:100] + ('...' if len(content) > 100 else ''),
                            'icon': '/static/images/logo.png',
                            'url': '/menu',
                            'badge': max(1, total_badge)
                        }
                        import threading
                        def _do_push(_subs, _data):
                            for _sub in _subs:
                                try:
                                    send_push_notification(_sub, _data)
                                except Exception:
                                    pass
                        threading.Thread(
                            target=_do_push,
                            args=(list(subscriptions), dict(notification_data)),
                            daemon=True
                        ).start()
                        _dbg(f"🔔 Notification push lancée en background pour {recipient_email}")
                except Exception as e:
                    _dbg(f"⚠️ Erreur envoi notification push: {e}")
                
                # Pas de flash() ici → évite double notification (flash sur /comments + flash sur /menu)
                # La confirmation est faite via ?sent=1 (toast JS local, sans session flash)
                recipient_name = recipient[1] if recipient[1] else recipient[0]
                if request.headers.get('X-Requested-With') == 'fetch':
                    conn.close()
                    return jsonify({'success': True, 'recipient_name': recipient_name})
                return redirect(url_for('messages.comments') + f'?sent=1&to={recipient_name}')
            else:
                if request.headers.get('X-Requested-With') == 'fetch':
                    conn.close()
                    return jsonify({'success': False, 'error': 'Destinataire invalide'}), 400
                flash("Destinataire invalide.", "danger")
        else:
            if request.headers.get('X-Requested-With') == 'fetch':
                conn.close()
                return jsonify({'success': False, 'error': 'Message ou destinataire manquant'}), 400
            flash("Veuillez sélectionner un destinataire et écrire un message.", "danger")
        
        return redirect(url_for('messages.comments'))

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
        # Convertir le timestamp UTC→Paris pour l'affichage
        timestamp = to_paris(timestamp) or timestamp
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
    _did_mark_any = False
    for msg in messages_data:
        if msg['message_type'] == 'private':
            # Messages reçus directement par moi
            if msg['is_received_by_me'] and not msg['is_me'] and not msg['is_read_by_me']:
                mark_message_as_read(msg['id'], session['user'])
                msg['is_read_by_me'] = True
                _did_mark_any = True
            # Messages pour un enfant : le parent lit au nom de l'enfant
            # (l'enfant n'a pas de téléphone, il consulte sur le téléphone du parent)
            if msg['recipient_is_child'] and not msg['is_read_by_recipient']:
                mark_message_as_read(msg['id'], msg['recipient_email'])
                msg['is_read_by_recipient'] = True
                _did_mark_any = True

    # 🔌 Si on a marqué des messages comme lus, prévenir TOUS les clients
    # (l'expéditeur voit son badge "lu", le destinataire voit sa pastille s'éteindre)
    if _did_mark_any:
        try:
            safe_socketio_emit('all_messages_read', {
                'reader_email': session['user'],
                'house_id': house_id
            }, namespace='/', room=f'house_{house_id}', broadcast=True)
        except Exception:
            pass

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
        
        # Préparer les 3 champs avatar séparément (compatibles avec le template comments.html)
        _av_url = None
        _av_file = None
        _av_emoji = None
        if player_avatar_file:
            _av_file = player_avatar_file
        elif player_avatar_url:
            # Convertir v8 → v7 (fond transparent par défaut)
            if 'dicebear.com/8.x' in player_avatar_url:
                player_avatar_url = player_avatar_url.replace('dicebear.com/8.x', 'dicebear.com/7.x')
            _av_url = player_avatar_url
        elif player_avatar and len(str(player_avatar)) <= 4:
            _av_emoji = player_avatar
        elif player_avatar:
            # C'est un seed DiceBear - construire l'URL
            try:
                c.execute("SELECT avatar_style FROM users WHERE email=?", (player_email,))
                style_row = c.fetchone()
                player_style = style_row[0] if style_row and style_row[0] else 'adventurer'
            except:
                player_style = 'adventurer'
            _av_url = f"https://api.dicebear.com/7.x/{player_style}/svg?seed={player_avatar}&backgroundColor=transparent"
        else:
            # Aucun avatar - générer un DiceBear par défaut
            seed = player_email.split('@')[0] if player_email else 'default'
            _av_url = f"https://api.dicebear.com/7.x/adventurer/svg?seed={seed}&backgroundColor=transparent"

        available_players.append({
            'email': player_email,
            'name': player_name if player_name else player_email.split('@')[0],
            'avatar_url': _av_url,
            'avatar_file': _av_file,
            'avatar': _av_emoji,
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
    
    # ✅ Auto-marquer comme lus tous les messages REÇUS (private) dès l'ouverture de la page
    for msg in messages_data:
        if not msg['is_me'] and not msg['is_read_by_me'] and msg.get('message_type') == 'private':
            mark_message_as_read(msg['id'], session['user'])
            msg['is_read_by_me'] = True

    # Compter les messages non lus (devrait être 0 après auto-marquage)
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


@messages_bp.route('/baby_messages')
def baby_messages():
    """
    Page dédiée aux messages de tracking bébé uniquement.
    Accessible via le bouton rose sous le menu burger.
    
    COMPORTEMENT :
    - Messages consultables uniquement (pas de notif, pas de marquage lu/non-lu)
    - Suppression automatique après 1 mois
    - Historique visible par tous les membres de la maison
    """
    from app import (get_db_connection, now_paris, _dbg,
                     mark_message_as_read, validate_avatar_file,
                     to_paris, get_house_players_points)
    if 'user' not in session:
        flash("Connecte-toi pour accéder aux messages bébé", "warning")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        flash("Tu dois rejoindre une maison pour accéder aux messages", "warning")
        return redirect(url_for('menu') + '?nav=1')
    
    house_id = user_row[0]
    current_user_name = user_row[1] if user_row[1] else session['user'].split('@')[0]

    # 🗑️ NETTOYAGE AUTOMATIQUE : Supprimer les messages de plus d'un mois
    from datetime import datetime, timedelta
    one_month_ago = (now_paris() - timedelta(days=30)).isoformat()
    
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
        # Convertir le timestamp UTC→Paris pour l'affichage
        timestamp = to_paris(timestamp) or timestamp
        
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


@messages_bp.route('/api/mark_type_read', methods=['POST'])
def api_mark_type_read():
    """
    Marque tous les messages d'un type donné comme lus pour l'utilisateur actuel.
    Utilisé pour décrémenter les pastilles (task_added, baby_tracking, courses_added).
    """
    from app import get_db_connection
    if 'user' not in session:
        return jsonify({'success': False}), 401
    data = request.get_json() or {}
    msg_type = data.get('type', '')
    if msg_type not in ('task_added', 'baby_tracking', 'courses_added'):
        return jsonify({'success': False, 'error': 'Type invalide'}), 400
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            conn.close()
            return jsonify({'success': False}), 400
        house_id = row[0]
        c.execute("""
            SELECT m.id FROM messages m
            WHERE m.house_id = ? AND m.message_type = ?
            AND NOT EXISTS (
                SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?
            )
        """, (house_id, msg_type, session['user']))
        rows = c.fetchall()
        for r in rows:
            c.execute("""
                INSERT INTO message_reads (message_id, user_email)
                VALUES (?, ?) ON CONFLICT(message_id, user_email) DO NOTHING
            """, (r[0], session['user']))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'marked': len(rows)})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@messages_bp.route('/mark_all_messages_read', methods=['POST'])
def mark_all_messages_read():
    """
    Marque tous les messages reçus par l'utilisateur comme lus.
    Retourne le nouveau compteur de messages non lus.
    """
    from app import (get_db_connection, mark_message_as_read,
                     get_unread_message_count, get_unread_messages_by_sender,
                     safe_socketio_emit)
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

    # Émettre immédiatement la descente à 0 vers tous les appareils de la maison
    safe_socketio_emit('unread_count_update', {
        'user_email': session['user'],
        'unread_received': 0
    }, namespace='/', room=f'house_{house_id}', broadcast=True)

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


@messages_bp.route('/mark_single_message_read_for_child', methods=['POST'])
def mark_single_message_read_for_child():
    """
    Permet à un parent de marquer UN seul message comme lu au nom d'un enfant.
    Utilisé quand le parent lit un message spécifique à l'enfant.
    """
    from app import (get_db_connection, mark_message_as_read, safe_socketio_emit)
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


@messages_bp.route('/mark_single_message_read', methods=['POST'])
def mark_single_message_read():
    """
    Permet à l'utilisateur de marquer UN seul message reçu comme lu.
    Utilisé pour marquer individuellement les messages reçus.
    """
    from app import (get_db_connection, mark_message_as_read, safe_socketio_emit,
                     get_unread_message_count, get_unread_messages_by_sender,
                     get_unread_messages_sent_to)
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


@messages_bp.route('/api/unread_messages_count', methods=['GET'])
def api_unread_messages_count():
    """
    API pour récupérer le nombre de messages non lus de l'utilisateur actuel.
    Utilisé pour rafraîchir les badges après réception d'un message pour enfant.
    """
    from app import (get_db_connection, _dbg,
                     get_unread_message_count, get_unread_messages_by_sender)
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


@messages_bp.route('/mark_messages_read_for_child', methods=['POST'])
def mark_messages_read_for_child():
    """
    Permet à un parent de marquer les messages comme lus au nom d'un enfant.
    Utilisé quand le parent lit les messages à l'enfant en personne.
    """
    from app import get_db_connection, mark_message_as_read
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
