from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify, flash, make_response
import os
import base64

players_bp = Blueprint('players', __name__)

# ========================================
# Routes pour la gestion des joueurs
# ========================================

@players_bp.route('/manage_players')
def manage_players():
    """Page de gestion des joueurs de la maison"""
    from app import assign_player_color, get_db_connection, validate_avatar_file
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('auth.login'))
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer la maison de l'utilisateur actuel
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        
        if not user_house or not user_house[0]:
            conn.close()
            flash("Vous devez d'abord rejoindre une maison", "warning")
            return redirect(url_for('menu') + '?nav=1')
        
        house_id = user_house[0]
        
        # Récupérer le nom de la maison
        c.execute("SELECT name FROM houses WHERE id=?", (house_id,))
        house_row = c.fetchone()
        house_name = house_row[0] if house_row else ""
        
        # Récupérer tous les joueurs de cette maison (inclut avatar_style pour DiceBear)
        c.execute("""
            SELECT email, name, avatar, avatar_file, avatar_url, player_color, avatar_style
            FROM users
            WHERE house_id=?
            ORDER BY name
        """, (house_id,))
        
        players = []
        for row in c.fetchall():
            email, name, avatar, avatar_file, avatar_url, player_color, avatar_style = row
            
            # Assigner une couleur si le joueur n'en a pas encore
            if not player_color:
                player_color = assign_player_color(email, house_id)
            
            # Convertir v8 → v7 et supprimer backgroundColor (fond coloré indésirable)
            import re as _re_mp
            if avatar_url and 'dicebear.com/8.x' in avatar_url:
                avatar_url = avatar_url.replace('dicebear.com/8.x', 'dicebear.com/7.x')
            if avatar_url and 'backgroundColor' in avatar_url:
                avatar_url = _re_mp.sub(r'[&?]backgroundColor=[^&]*', '', avatar_url).rstrip('?&')
            players.append({
                'email': email,
                'name': name,
                'avatar': avatar,
                'avatar_file': validate_avatar_file(avatar_file),
                'avatar_url': avatar_url,
                'avatar_style': avatar_style if avatar_style else 'adventurer',
                'color': player_color
            })
        
        conn.close()
        
        print(f'🏠 MANAGE_PLAYERS players={[(p["email"],p["name"],p["avatar"],p["avatar_url"]) for p in players]}', flush=True)
        return render_template('manage_players.html', 
                             players=players, 
                             house_name=house_name,
                             house_id=house_id,
                             hide_header=True)
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': 'Une erreur est survenue, réessaie.'}), 500


@players_bp.route('/edit_player/<path:email>')
def edit_player(email):
    """Page de modification d'un joueur"""
    from app import get_db_connection
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Vérifier que l'utilisateur actuel et le joueur à modifier sont dans la même maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_house = c.fetchone()
    
    c.execute("SELECT house_id, email, name, avatar, avatar_file, avatar_url, avatar_style FROM users WHERE email=?", (email,))
    player_row = c.fetchone()
    
    if not user_house or not player_row or user_house[0] != player_row[0]:
        conn.close()
        flash("Non autorisé", "error")
        return redirect(url_for('players.manage_players'))
    
    # Supprimer backgroundColor des URLs DiceBear (fond coloré indésirable)
    import re as _re_ep
    ep_avatar_url = player_row[5]
    if ep_avatar_url and 'backgroundColor' in ep_avatar_url:
        ep_avatar_url = _re_ep.sub(r'[&?]backgroundColor=[^&]*', '', ep_avatar_url).rstrip('?&')
    player = {
        'email': player_row[1],
        'name': player_row[2],
        'avatar': player_row[3],
        'avatar_file': player_row[4],
        'avatar_url': ep_avatar_url,
        'avatar_style': player_row[6] if player_row[6] else 'adventurer'
    }
    
    conn.close()
    
    return render_template('edit_player.html', player=player, hide_header=True)


@players_bp.route('/update_player', methods=['POST'])
def update_player():
    """Mettre à jour le nom et l'avatar d'un joueur"""
    from app import SOCKETIO_AVAILABLE, _dbg, get_db_connection, propagate_player_name_change, socketio
    if 'user' not in session:
        _dbg("❌ UPDATE_PLAYER: Utilisateur non connecté")
        return jsonify({'success': False, 'error': 'Non connecté'})
    
    try:
        email = request.form.get('email')
        name = request.form.get('name', '').strip()
        avatar_type = request.form.get('avatar_type', '').strip()
        
        print("🔍 UPDATE_PLAYER - Données reçues:", flush=True)
        print(f"🔍 UPDATE_PLAYER email={email} name={name} avatar_type={avatar_type}", flush=True)
        _dbg(f"   name: {name}")
        _dbg(f"   avatar_type: '{avatar_type}'")
        _dbg(f"   avatar: {request.form.get('avatar')}")
        _dbg(f"   avatar_style: {request.form.get('avatar_style')}")
        _dbg(f"   session['user']: {session.get('user')}")
        _dbg(f"   Tous les champs: {dict(request.form)}")
        
        if not email:
            _dbg("❌ UPDATE_PLAYER: Email manquant")
            return jsonify({'success': False, 'error': 'Email requis'})
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Vérifier que l'utilisateur actuel et le joueur à modifier sont dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        
        c.execute("SELECT house_id FROM users WHERE email=?", (email,))
        player_house = c.fetchone()
        
        _dbg(f"   user_house: {user_house}")
        _dbg(f"   player_house: {player_house}")
        
        if not user_house or not player_house:
            conn.close()
            _dbg("❌ UPDATE_PLAYER: Utilisateur ou joueur non trouvé")
            return jsonify({'success': False, 'error': 'Utilisateur ou joueur non trouvé'})
            
        if user_house[0] != player_house[0]:
            conn.close()
            _dbg("❌ UPDATE_PLAYER: Maisons différentes, non autorisé")
            return jsonify({'success': False, 'error': 'Non autorisé - vous devez être dans la même maison'})
        
        # 📛 Récupérer l'ancien nom AVANT la mise à jour (pour propager le changement)
        c.execute("SELECT name FROM users WHERE email=?", (email,))
        old_name_row = c.fetchone()
        old_name = old_name_row[0] if old_name_row and old_name_row[0] else None
        
        # Préparer la mise à jour
        update_parts = []
        update_values = []
        
        if name:
            update_parts.append("name=?")
            update_values.append(name)
            _dbg(f"   ✅ Ajout du nom à la mise à jour: '{name}'")
        
        # Gérer l'avatar SEULEMENT si avatar_type est fourni et valide
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
                    _dbg(f"   ✅ Avatar emoji: {emoji}")
        
        elif avatar_type == 'dicebear':
            # Avatar DiceBear : récupérer le seed et construire l'URL
            seed = request.form.get('avatar', '').strip()
            style = request.form.get('avatar_style', 'avataaars').strip()
            _dbg(f"✅ Avatar DiceBear détecté - seed: {seed}, style: {style}")
            if seed:
                dicebear_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={seed}"
                update_parts.append("avatar_url=?")
                update_values.append(dicebear_url)
                # Stocker le seed dans avatar pour le retrouver
                update_parts.append("avatar=?")
                update_values.append(seed)
                # Stocker le style
                update_parts.append("avatar_style=?")
                update_values.append(style)
                # Effacer avatar_file
                update_parts.append("avatar_file=?")
                update_values.append(None)
                _dbg(f"   URL construite: {dicebear_url}")
                _dbg(f"   Champs à mettre à jour: avatar={seed}, avatar_style={style}, avatar_url={dicebear_url}")
        
        elif avatar_type == 'file':
            # Sélection d'une image PNG existante depuis la galerie
            avatar_filename = request.form.get('avatar', '').strip()
            _dbg(f"   Avatar file détecté: {avatar_filename}")
            if avatar_filename and avatar_filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                update_parts.append("avatar_file=?")
                update_values.append(avatar_filename)
                # Effacer les autres types d'avatar
                update_parts.append("avatar=?")
                update_values.append(None)
                update_parts.append("avatar_url=?")
                update_values.append(None)
                _dbg(f"   ✅ Avatar file conservé: {avatar_filename}")
        
        elif avatar_type == 'photo':
            # Gérer l'upload de fichier → data URI en DB (compatible Render)
            if 'avatar_file' in request.files:
                file = request.files['avatar_file']
                if file and file.filename:
                    raw_data = file.read()
                    try:
                        from PIL import Image, ImageOps
                        import io as _io_p
                        img = Image.open(_io_p.BytesIO(raw_data))
                        img = ImageOps.exif_transpose(img)
                        img = img.convert('RGB')
                        img.thumbnail((400, 400), Image.LANCZOS)
                        buf = _io_p.BytesIO()
                        img.save(buf, format='JPEG', quality=75, optimize=True)
                        raw_data = buf.getvalue()
                    except ImportError:
                        pass
                    data_uri = "data:image/jpeg;base64," + base64.b64encode(raw_data).decode('utf-8')
                    update_parts.append("avatar_url=?")
                    update_values.append(data_uri)
                    # Effacer les autres types d'avatar
                    update_parts.append("avatar=?")
                    update_values.append(None)
                    update_parts.append("avatar_file=?")
                    update_values.append(None)
                    _dbg(f"   ✅ Photo stockée en DB (data URI, {len(data_uri)} chars)")
        else:
            # Si avatar_type est vide ou inconnu, ne pas toucher à l'avatar
            _dbg(f"   ℹ️ Avatar type vide ou inconnu ('{avatar_type}'), conservation de l'avatar actuel")
        
        print(f"📋 update_parts={update_parts}, avatar_type={avatar_type}, seed={request.form.get(chr(97)+chr(118)+chr(97)+chr(116)+chr(97)+chr(114))}", flush=True)
        if update_parts:
            update_values.append(email)
            query = f"UPDATE users SET {', '.join(update_parts)} WHERE email=?"
            _dbg(f"   📝 Requête SQL: {query}")
            _dbg(f"   📝 Valeurs: {update_values}")
            c.execute(query, update_values)
            print(f"✅ UPDATE_PLAYER SQL OK rowcount={c.rowcount}", flush=True)
            
            conn.commit()
            print("✅ COMMIT OK", flush=True)
            
            # 📛 Propager le changement de nom dans les messages existants
            if name and old_name and name != old_name:
                house_id = user_house[0]
                try:
                    propagate_player_name_change(c, email, old_name, name, house_id)
                    conn.commit()
                except Exception as prop_err:
                    print(f"⚠️ propagate ignoré: {prop_err}", flush=True)
                _dbg(f"📛 Nom du joueur changé: '{old_name}' → '{name}' pour {email}")
                
                # Mettre à jour la session si c'est l'utilisateur connecté
                if email == session.get('user'):
                    session['user_name'] = name
                    if 'name' in session:
                        session['name'] = name
            
            # 🔌 WEBSOCKET: Notifier tous les joueurs du changement
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    house_id = user_house[0]
                    # Récupérer les données fraîches après commit pour diffuser l'avatar réel
                    c.execute("SELECT name, avatar, avatar_url, avatar_file FROM users WHERE email=?", (email,))
                    fresh = c.fetchone()
                    if fresh:
                        player_data = {
                            'email': email,
                            'name': fresh[0],
                            'avatar': fresh[1],
                            'avatar_url': fresh[2],
                            'avatar_file': fresh[3]
                        }
                        socketio.emit('player_avatar_update', player_data, namespace='/', to=f'house_{house_id}')
                    # Si le nom a changé, notifier aussi pour rafraîchir les affichages
                    if name and old_name and name != old_name:
                        socketio.emit('player_name_updated', {
                            'email': email, 
                            'old_name': old_name, 
                            'new_name': name
                        }, namespace='/', to=f'house_{house_id}')
                    _dbg(f"🔌 WebSocket: Diffusion changement pour {email} (room: house_{house_id})")
                except Exception as ws_err:
                    print(f"⚠️ Erreur WebSocket: {ws_err}", flush=True)
        else:
            _dbg("   ⚠️ Aucune modification à effectuer (update_parts vide)")
        
        conn.close()
        
        print("✅✅✅ UPDATE_PLAYER terminé avec succès", flush=True)
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"❌❌❌ [ERROR update_player] {e}", flush=True)
        import traceback
        _dbg(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})


@players_bp.route('/delete_player', methods=['POST'])
def delete_player():
    """Supprimer un joueur de la maison (mettre house_id à NULL)"""
    from app import _dbg, get_db_connection, socketio, validate_avatar_file
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
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Vérifier que l'utilisateur actuel et le joueur à supprimer sont dans la même maison
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        
        c.execute("SELECT house_id FROM users WHERE email=?", (email,))
        player_house = c.fetchone()
        
        if not user_house or not player_house or user_house[0] != player_house[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        house_id = user_house[0]
        
        # Récupérer le nom du joueur avant suppression
        c.execute("SELECT name FROM users WHERE email=?", (email,))
        player_row = c.fetchone()
        player_name = player_row[0] if player_row and player_row[0] else email.split('@')[0]
        
        # Supprimer le joueur de la maison (mettre house_id à NULL)
        c.execute("UPDATE users SET house_id=NULL WHERE email=?", (email,))
        conn.commit()
        
        # Récupérer la liste mise à jour des joueurs
        c.execute("""
            SELECT email, name, avatar, avatar_file, avatar_url, avatar_style, points, player_color 
            FROM users 
            WHERE house_id = ?
            ORDER BY name
        """, (house_id,))
        
        players = c.fetchall()
        players_data = []
        for p in players:
            email_p, name_p, avatar_p, avatar_file_p, avatar_url_p, avatar_style_p, points_p, player_color_p = p
            
            # Gérer l'URL de l'avatar
            clean_avatar_url = None
            valid_file_p = validate_avatar_file(avatar_file_p)
            if valid_file_p:
                clean_avatar_url = f"/static/avatars/{valid_file_p}"
            elif avatar_url_p:
                clean_avatar_url = avatar_url_p
            elif avatar_p:
                # Si c'est un seed DiceBear (8 caractères alphanumériques)
                if len(avatar_p) == 8 and avatar_p.isalnum():
                    style = avatar_style_p if avatar_style_p else 'lorelei'
                    clean_avatar_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={avatar_p}"
                else:
                    clean_avatar_url = avatar_p
            
            players_data.append({
                'email': email_p,
                'name': name_p or email_p.split('@')[0],
                'avatar_url': clean_avatar_url,
                'points': points_p or 0,
                'player_color': player_color_p
            })
        
        conn.close()
        
        # Émettre l'événement WebSocket
        _dbg(f"🔌 WebSocket: Joueur '{player_name}' supprimé (room: house_{house_id})")
        socketio.emit('players_list_update', {
            'players': players_data,
            'deleted_player': player_name,
            'action': 'player_deleted'
        }, namespace='/', room=f'house_{house_id}')
        
        return jsonify({'success': True})
        
    except Exception as e:
        _dbg(f"[ERROR delete_player] {e}")
        return jsonify({'success': False, 'error': str(e)})


# ========================================
# Routes pour ajouter des joueurs
# ========================================

@players_bp.route('/add_players')
def add_players():
    """Page de choix : ajouter enfants ou inviter partenaires"""
    from app import get_db_connection, get_house_players_points, now_paris, validate_avatar_file
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('auth.login'))
    
    # Récupérer les joueurs de la maison pour afficher le header
    players = []
    current_user_name = session.get('user', '')
    player1_name = None
    player1_avatar = None
    player1_avatar_url = None
    current_user_daily_points = 0
    house_health = 100
    
    conn = get_db_connection()
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
            valid_file = validate_avatar_file(avatar_file)
            if valid_file:
                player1_avatar_url = url_for('static', filename='avatars/' + valid_file)
        
        # Points du jour pour le joueur actuel
        from datetime import date
        today = now_paris().date().isoformat()
        c.execute("SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at)=?", (session['user'], today))
        pts = c.fetchone()
        current_user_daily_points = int(pts[0]) if pts and pts[0] else 0
        
        # Ajouter les points du jour à chaque joueur
        for p in players:
            email = p.get('email')
            if email:
                c.execute("SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at)=?", (email, today))
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


@players_bp.route('/update_profile', methods=['POST'])
def update_profile():
    from app import SOCKETIO_AVAILABLE, _dbg, get_db_connection, propagate_player_name_change, save_photo_from_base64, socketio
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('auth.login'))
    
    name = request.form.get('name', '').strip().capitalize()
    avatar = request.form.get('avatar', '').strip()
    avatar_style = request.form.get('avatar_style', 'lorelei').strip()
    photo_data = request.form.get('photo_data')
    house_name_input = request.form.get('house_name', '').strip()
    
    import sys
    _dbg(f"🔍 UPDATE PROFILE: name={name}, avatar={avatar}, style={avatar_style}")
    sys.stdout.flush()
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # 📛 Récupérer l'ancien nom AVANT la mise à jour (pour propager le changement)
    old_name = None
    profile_house_id = None
    if name:
        c.execute("SELECT name, house_id FROM users WHERE email=?", (session['user'],))
        old_row = c.fetchone()
        old_name = old_row[0] if old_row and old_row[0] else None
        profile_house_id = old_row[1] if old_row else None
    
    update_fields = []
    update_values = []
    
    # Mettre à jour le nom
    if name:
        update_fields.append("name=?")
        update_values.append(name)
        session['user_name'] = name
        if 'name' in session:
            session['name'] = name
    
    # Gérer la photo uploadée (priorité maximale) — stockage data URI en DB
    if photo_data and photo_data.startswith('data:image'):
        photo_data_uri = save_photo_from_base64(photo_data)
        if photo_data_uri:
            update_fields.extend(["avatar_url=?", "avatar_file=?", "avatar=?", "avatar_style=?"])
            update_values.extend([photo_data_uri, '', '', ''])
            session['user_avatar_url'] = photo_data_uri
            _dbg(f"✅ Photo stockée en DB (data URI, {len(photo_data_uri)} chars)")
    
    # Gérer l'avatar si pas de photo
    elif avatar:
        _dbg(f"   📝 Traitement avatar: '{avatar}'")
        is_file = avatar.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        is_emoji = len(avatar) <= 4 and any(ord(c) > 127 for c in avatar)
        is_dicebear = not is_file and not is_emoji
        _dbg(f"   📋 Type détecté: file={is_file}, emoji={is_emoji}, dicebear={is_dicebear}")
        
        if is_file:
            update_fields.extend(["avatar_file=?", "avatar=?", "avatar_url=?", "avatar_style=?"])
            update_values.extend([avatar, '', '', ''])
            session['user_avatar'] = avatar
            _dbg(f"✅ Fichier: {avatar}")
            
        elif is_emoji:
            update_fields.extend(["avatar=?", "avatar_file=?", "avatar_url=?", "avatar_style=?"])
            update_values.extend([avatar, '', '', ''])
            session['user_avatar'] = avatar
            _dbg(f"✅ Emoji: {avatar}")
            
        else:  # is_dicebear
            dicebear_url = f"https://api.dicebear.com/7.x/{avatar_style}/svg?seed={avatar}"
            update_fields.extend(["avatar=?", "avatar_url=?", "avatar_style=?", "avatar_file=?"])
            update_values.extend([avatar, dicebear_url, avatar_style, ''])
            session['user_avatar'] = avatar
            _dbg(f"✅ DiceBear: seed={avatar}, style={avatar_style}, url={dicebear_url}")
            _dbg(f"   🔧 update_fields: {update_fields}")
            _dbg(f"   🔧 update_values: {update_values}")
            sys.stdout.flush()
        
        if 'user_photo' in session:
            del session['user_photo']
    
    # Toujours marquer le profil comme complété (registration_step)
    update_fields.append("registration_step=?")
    update_values.append('profile_created')

    # Exécuter la mise à jour
    update_values.append(session['user'])
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE email=?"
    try:
        c.execute(query, update_values)
        print(f"✅ UPDATE OK: fields={update_fields}", flush=True)
    except Exception as e:
        print(f"❌ ERREUR UPDATE: {e}, query={query}", flush=True)
        import traceback; traceback.print_exc()
        conn.rollback()
        conn.close()
        flash(f"Erreur sauvegarde: {e}", "danger")
        return redirect(url_for('players.create_profile'))
    
    # Mettre à jour le nom de la maison
    if house_name_input:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        user_house = c.fetchone()
        if user_house and user_house[0]:
            c.execute("UPDATE houses SET house_name=?, name=? WHERE id=?", 
                      (house_name_input, house_name_input, user_house[0]))
    
    conn.commit()
    
    # 📛 Propager le changement de nom dans les messages existants
    if name and old_name and name != old_name and profile_house_id:
        try:
            propagate_player_name_change(c, session['user'], old_name, name, profile_house_id)
            conn.commit()
        except Exception as prop_err:
            print(f"⚠️ propagate ignoré: {prop_err}", flush=True)
        _dbg(f"📛 Pseudo mis à jour via profil: '{old_name}' → '{name}' pour {session['user']}")
        
        # 🔌 Notifier via WebSocket
        if SOCKETIO_AVAILABLE and socketio:
            try:
                socketio.emit('player_name_updated', {
                    'email': session['user'],
                    'old_name': old_name,
                    'new_name': name
                }, namespace='/', room=f'house_{profile_house_id}')
            except Exception as ws_err:
                _dbg(f"⚠️ Erreur WebSocket changement nom: {ws_err}")
    conn.close()
    
    flash("Profil mis à jour avec succès ! ✨", "success")
    return redirect(url_for('menu') + '?nav=1')


# Routes pour la création de profil
@players_bp.route('/create_profile')
def create_profile():
    from app import _dbg, get_db_connection
    _dbg(f"🎭 CREATE_PROFILE GET: user={session.get('user')}, house_name={session.get('house_name')}")
    
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('auth.signup_email'))
    
    # Vérifier si l'utilisateur a déjà un profil (mode modification)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, avatar, avatar_file, house_id, registration_step, avatar_url, avatar_style FROM users WHERE email=?", (session['user'],))
    user = c.fetchone()
    
    change_avatar = False
    current_name = ''
    current_avatar = ''
    current_avatar_file = ''
    current_avatar_url = ''
    current_avatar_style = ''
    current_house_name = ''
    
    if user:
        current_name = user[0] or ''
        current_avatar = user[1] or ''  # Avatar prédéfini (nom de fichier comme homme.png)
        current_avatar_file = user[2] or ''  # Photo uploadée (fichier JPG)
        house_id = user[3]
        registration_step = user[4] or ''
        current_avatar_url = user[5] or ''  # URL DiceBear
        current_avatar_style = user[6] or 'lorelei'  # Style DiceBear
        
        _dbg(f"   📊 User data: name={current_name}, registration_step={registration_step}, house_id={house_id}")
        
        # Mode modification uniquement si le profil est réellement terminé
        # (évite de basculer en édition pendant l'onboarding quand un nom existe déjà)
        if registration_step in ('profile_created', 'complete'):
            change_avatar = True
            _dbg(f"   ⚠️ Profil déjà présent (name={current_name}, step={registration_step}) -> mode modification")
        else:
            _dbg(f"   ✅ Première création de profil")
        
        # Récupérer le nom de la maison si existe
        if house_id:
            c.execute("SELECT house_name FROM houses WHERE id=?", (house_id,))
            house = c.fetchone()
            if house and house[0]:
                current_house_name = house[0]
    
    conn.close()
    
    _dbg(f"   🎨 Affichage create_profile.html (change_avatar={change_avatar})")
    
    return render_template('create_profile.html', 
                           change_avatar=change_avatar,
                           current_name=current_name,
                           current_avatar=current_avatar,
                           current_avatar_file=current_avatar_file,
                           current_avatar_url=current_avatar_url,
                           current_avatar_style=current_avatar_style,
                           current_house_name=current_house_name)

@players_bp.route('/create_profile', methods=['POST'])
def create_profile_post():
    from app import _dbg, generate_house_code, get_db_connection, now_paris, save_photo_from_base64
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('auth.signup_email'))
    
    name = request.form.get('name', '').strip().capitalize()
    bio = request.form.get('bio', '').strip()
    avatar = request.form.get('avatar', '').strip()
    avatar_style = request.form.get('avatar_style', 'lorelei').strip()
    photo_data = request.form.get('photo_data')
    house_name_input = request.form.get('house_name', '').strip()
    
    import sys
    _dbg(f"🔍 CREATE PROFILE: name={name}, avatar={avatar}, style={avatar_style}")
    sys.stdout.flush()
    
    if not name:
        flash("Le nom est requis", "danger")
        return render_template('create_profile.html')
    
    # Gérer la photo uploadée — stockage data URI en DB (compatible Render)
    photo_data_uri = None
    if photo_data and photo_data.startswith('data:image'):
        photo_data_uri = save_photo_from_base64(photo_data)
        if not photo_data_uri:
            flash("Erreur lors de la sauvegarde de la photo", "warning")
    
    # Mettre à jour le profil utilisateur
    conn = get_db_connection()
    c = conn.cursor()
    
    # Préparer les valeurs de mise à jour
    update_fields = ["name=?"]
    update_values = [name]
    
    if bio:
        update_fields.append("bio=?")
        update_values.append(bio)
    
    # GESTION AVATAR : 3 cas possibles
    if photo_data_uri:
        # CAS 1: Photo uploadée → stockée en DB comme data URI dans avatar_url
        update_fields.extend(["avatar_url=?", "avatar_file=?", "avatar=?", "avatar_style=?"])
        update_values.extend([photo_data_uri, '', '', ''])
        _dbg(f"✅ Avatar = Photo stockée en DB (data URI, {len(photo_data_uri)} chars)")
        
    elif avatar:
        # Détecter le type d'avatar
        is_file = avatar.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        is_emoji = len(avatar) <= 4 and any(ord(c) > 127 for c in avatar)
        is_dicebear = not is_file and not is_emoji
        
        if is_file:
            # CAS 2: Fichier existant (femme.png, homme.png, etc.)
            update_fields.extend(["avatar_file=?", "avatar=?", "avatar_url=?", "avatar_style=?"])
            update_values.extend([avatar, '', '', ''])
            _dbg(f"✅ Avatar = Fichier: {avatar}")
            
        elif is_emoji:
            # CAS 3: Emoji
            update_fields.extend(["avatar=?", "avatar_file=?", "avatar_url=?", "avatar_style=?"])
            update_values.extend([avatar, '', '', ''])
            _dbg(f"✅ Avatar = Emoji: {avatar}")
            
        else:  # is_dicebear
            # CAS 4: DiceBear (seed)
            dicebear_url = f"https://api.dicebear.com/7.x/{avatar_style}/svg?seed={avatar}"
            update_fields.extend(["avatar=?", "avatar_url=?", "avatar_style=?", "avatar_file=?"])
            update_values.extend([avatar, dicebear_url, avatar_style, ''])
            _dbg(f"✅ Avatar = DiceBear: seed={avatar}, style={avatar_style}, url={dicebear_url}")
    
    # Finaliser la requête
    update_fields.append("registration_step=?")
    update_values.append('profile_created')
    update_values.append(session['user'])
    
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE email=?"
    c.execute(query, update_values)
    
    # Créer ou vérifier la maison
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_house = c.fetchone()
    
    if not user_house or not user_house[0]:
        # Récupérer les infos de session pour créer la maison
        house_type = session.get('house_type', 'family')
        house_name = session.get('house_name', 'Notre Foyer')
        
        from datetime import date
        house_code = generate_house_code()
        today = now_paris().date().isoformat()
        c.execute("""
            INSERT INTO houses (name, house_name, house_type, level, health, mood, code, progress, last_reset_date) 
            VALUES (?, ?, ?, 1, 100, 'happy', ?, 0, ?)
        """, (house_name, house_name, house_type, house_code, today))
        house_id = c.lastrowid
        c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, session['user']))
    
    conn.commit()
    conn.close()
    
    # Nettoyer les infos temporaires de session
    session.pop('house_type', None)
    session.pop('house_name', None)
    session['user_name'] = name
    session['registration_step'] = 'complete'
    
    return redirect(url_for('auth.splash'))


@players_bp.route('/profil')
def profil():
    return profil_joueur(session.get('user', ''))

@players_bp.route('/profil/<path:player_email>')
def profil_joueur(player_email):
    from app import PARIS_TZ, _USE_PG, get_db_connection, get_house_players_points, get_unread_count_by_type, now_paris
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    current_user_name = session.get('user', '')
    # Rediriger vers /profil si c'est son propre profil (URL propre)
    if player_email == current_user_name and request.endpoint == 'profil_joueur':
        return redirect(url_for('players.profil'))
    is_own_profile = (player_email == current_user_name)
    player1_name = None
    player1_avatar = None
    player1_avatar_file = None
    player1_avatar_url = None
    house_name = None
    house_id = None
    viewer_house_id = None
    players = []
    unread_baby_tracking = 0
    has_baby_tracking = False
    daily_report = []
    player1_points = 0
    my_rewards_available = []
    my_rewards_used = []
    gameplay_notifs = []
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Maison du visiteur (pour vérification sécurité)
        try:
            c.execute("SELECT house_id FROM users WHERE email=?", (current_user_name,))
            vr = c.fetchone()
            if vr:
                viewer_house_id = vr[0]
        except Exception:
            pass
        # Données du joueur affiché
        try:
            c.execute("SELECT name, avatar, avatar_file, house_id, avatar_url FROM users WHERE email=?", (player_email,))
            row = c.fetchone()
            if row:
                player1_name, player1_avatar, player1_avatar_file, house_id, player1_avatar_url = row
        except Exception:
            pass
        # Sécurité : le joueur affiché doit être dans la même maison
        if house_id and viewer_house_id and house_id != viewer_house_id:
            conn.close()
            return redirect(url_for('menu') + '?nav=1')
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
            except Exception:
                players = []
            try:
                c.execute("SELECT COUNT(*) FROM baby_tracking WHERE house_id=?", (house_id,))
                has_baby_tracking = (c.fetchone()[0] or 0) > 0
            except Exception:
                pass
            try:
                today = now_paris().date().strftime('%Y-%m-%d')
                c.execute("SELECT email, COUNT(*) FROM tasks WHERE house_id=? AND date=? AND done=1 GROUP BY email", (house_id, today))
                daily_report = [{'email': r[0], 'count': r[1]} for r in c.fetchall()]
            except Exception:
                daily_report = []
            if is_own_profile:
                try:
                    unread_baby_tracking = get_unread_count_by_type(current_user_name, house_id, 'baby_tracking', existing_conn=conn, include_own=True)
                except Exception:
                    pass
        # Récompenses : pour tout profil (pas seulement le sien)
        print(f"🎁 profil récompenses: requête pour user={player_email}", flush=True)
        try:
            c.execute("""
                SELECT id, reward_text, won_date
                FROM mystery_rewards
                WHERE user_email=? AND used=0
                ORDER BY id DESC
                LIMIT 3
            """, (player_email,))
            my_rewards_available = [{'id': r[0], 'text': r[1], 'date': r[2]} for r in c.fetchall()]
            print(f"🎁 Récompenses disponibles: {len(my_rewards_available)}", flush=True)
        except Exception as e:
            _dbg(f"❌ Erreur récompenses disponibles: {e}")
            import traceback; traceback.print_exc()
            my_rewards_available = []
        try:
            c.execute("""
                SELECT id, reward_text, won_date, used_date
                FROM mystery_rewards
                WHERE user_email=? AND used=1
                ORDER BY used_date DESC
            """, (player_email,))
            my_rewards_used = [{'id': r[0], 'text': r[1], 'won_date': r[2], 'used_date': r[3]} for r in c.fetchall()]
            print(f"🎁 Récompenses utilisées: {len(my_rewards_used)}", flush=True)
        except Exception as e:
            _dbg(f"❌ Erreur récompenses utilisées: {e}")
            import traceback; traceback.print_exc()
            my_rewards_used = []
        # ── Notifications gameplay reçues (bonus/malus/suspicions 48h) ──
        # Précharger les avatars des joueurs de la maison pour les bonus/malus
        _house_avatars = {}
        try:
            c.execute("SELECT name, avatar, avatar_file, avatar_url FROM users WHERE house_id=?", (house_id,))
            for _ua in c.fetchall():
                if _ua[0]:
                    _house_avatars[_ua[0]] = {'avatar': _ua[1], 'avatar_file': _ua[2], 'avatar_url': _ua[3]}
        except Exception:
            pass
        try:
            # Bonus et Malus reçus (48h)
            c.execute("""
                SELECT ct.task_name, ct.category, ct.points, ct.completed_at
                FROM completed_tasks ct
                WHERE ct.user_email=? AND ct.category IN ('bonus','malus')
                AND ct.completed_at >= datetime('now', '-48 hours')
                ORDER BY ct.completed_at DESC LIMIT 20
            """, (player_email,))
            seen_bonus = set()
            _jours_fr = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
            for r in c.fetchall():
                key = (r[0], r[1])  # (task_name, category) — éviter doublons
                if key not in seen_bonus:
                    seen_bonus.add(key)
                    # Parser "Malus de Anne : Vaisselle non rangée"
                    # → giver="Anne", reason="Vaisselle non rangée"
                    _raw = r[0] or ''
                    _giver = ''
                    _reason = ''
                    # Format attendu : "Bonus de Nom : Motif | Tâche" ou "💀 Malus de Nom : Motif"
                    import re as _re_bm
                    # Séparer la tâche ménagère si présente (après |)
                    _task_context = ''
                    _parse_raw = _raw
                    if ' | ' in _raw:
                        _parse_raw, _task_context = _raw.rsplit(' | ', 1)
                        _task_context = _task_context.strip()
                    _m = _re_bm.match(r'^(?:[^\w]*?)(?:Bonus|Malus)\s+de\s+(.+?)\s*:\s*(.+)$', _parse_raw)
                    if _m:
                        _giver = _m.group(1).strip()
                        _reason = _m.group(2).strip()
                    elif ' de ' in _raw:
                        # Fallback : "Malus de Anne" sans motif
                        _after_de = _raw.split(' de ', 1)[1].strip()
                        if ' : ' in _after_de:
                            _giver = _after_de.split(' : ', 1)[0].strip()
                            _reason = _after_de.split(' : ', 1)[1].strip()
                        else:
                            _giver = _after_de
                    # Convertir completed_at en heure Paris et formater "lundi à 9:03"
                    _date_str = ''
                    if r[3]:
                        try:
                            _raw_dt = str(r[3])[:19]
                            _dt = datetime.strptime(_raw_dt, '%Y-%m-%d %H:%M:%S')
                            # SQLite local: CURRENT_TIMESTAMP = UTC → convertir en Paris
                            # PostgreSQL Render: CURRENT_TIMESTAMP = déjà Paris → pas de conversion
                            if not _USE_PG and PARIS_TZ:
                                from zoneinfo import ZoneInfo as _ZI
                                _dt = _dt.replace(tzinfo=_ZI('UTC')).astimezone(PARIS_TZ).replace(tzinfo=None)
                            _jour = _jours_fr[_dt.weekday()]
                            _heure = f'{_dt.hour}:{_dt.minute:02d}'
                            _date_str = f'{_jour} à {_heure}'
                        except Exception:
                            _date_str = str(r[3])[:16].replace('T', ' ')
                    # Récupérer l'avatar du giver depuis le cache maison
                    _giver_avatar = ''
                    _giver_avatar_file = ''
                    _giver_avatar_url = ''
                    if _giver and _giver in _house_avatars:
                        _ga = _house_avatars[_giver]
                        _giver_avatar = _ga.get('avatar', '')
                        _giver_avatar_file = _ga.get('avatar_file', '')
                        _giver_avatar_url = _ga.get('avatar_url', '')
                    gameplay_notifs.append({
                        'text': r[0], 'type': r[1], 'points': r[2],
                        'date': _date_str,
                        'giver': _giver, 'reason': _reason,
                        'task_context': _task_context,
                        'giver_avatar': _giver_avatar,
                        'giver_avatar_file': _giver_avatar_file,
                        'giver_avatar_url': _giver_avatar_url
                    })
            # Suspicions reçues (où ce joueur est suspecté)
            c.execute("""
                SELECT s.task_name, s.status, u.name, s.created_at
                FROM suspicions s
                INNER JOIN users u ON s.suspecting_player_email = u.email
                WHERE s.suspected_player_email=?
                AND s.created_at >= datetime('now', '-48 hours')
                ORDER BY s.created_at DESC LIMIT 10
            """, (player_email,))
            for r in c.fetchall():
                gameplay_notifs.append({'text': r[0], 'type': 'suspicion', 'from': r[2], 'status': r[1], 'date': str(r[3]) if r[3] else ''})
            # Trier par date décroissante
            gameplay_notifs.sort(key=lambda x: x.get('date',''), reverse=True)
        except Exception:
            pass
        conn.close()
    except Exception:
        pass
    cp = next((p for p in players if p.get('email') == player_email), None)
    return render_template(
        'profil.html',
        current_user_name=current_user_name,
        player_email=player_email,
        is_own_profile=is_own_profile,
        player1_name=player1_name,
        player1_avatar=player1_avatar,
        player1_avatar_file=player1_avatar_file,
        player1_avatar_url=player1_avatar_url,
        house_name=house_name,
        players=players,
        cp=cp,
        player1_points=player1_points,
        daily_report=daily_report,
        unread_baby_tracking=unread_baby_tracking,
        my_rewards_available=my_rewards_available,
        my_rewards_used=my_rewards_used,
        gameplay_notifs=gameplay_notifs,
    )


# Simple route de test pour vérifier la connectivité (retourne OK en texte brut)


@players_bp.route('/api/avatar_proxy')
def avatar_proxy():
    """
    🚀 Proxy local pour les avatars DiceBear - cache en fichier local.
    Évite les appels directs au CDN externe api.dicebear.com depuis le navigateur.
    Usage: /api/avatar_proxy?style=adventurer&seed=xxx
    """
    import urllib.request as _urlreq
    import re as _re
    style = request.args.get('style', 'adventurer')
    seed = request.args.get('seed', 'default')
    # Sanitiser les entrées
    if not _re.match(r'^[a-zA-Z0-9_-]+$', style):
        style = 'adventurer'
    seed = _re.sub(r'[<>"\'\\]', '', str(seed))[:60]
    
    # Dossier de cache
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'avatars_cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = _re.sub(r'[^a-zA-Z0-9_-]', '_', f"{style}_{seed}")
    cache_file = os.path.join(cache_dir, f"{cache_key}.svg")
    
    # Servir depuis le cache si dispo
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            svg_data = f.read()
        resp = make_response(svg_data)
        resp.headers['Content-Type'] = 'image/svg+xml'
        resp.headers['Cache-Control'] = 'public, max-age=604800'  # 7 jours
        return resp
    
    # Sinon: fetcher depuis DiceBear et mettre en cache
    dicebear_url = f'https://api.dicebear.com/7.x/{style}/svg?seed={seed}'
    try:
        req = _urlreq.Request(dicebear_url, headers={'User-Agent': 'CleanBeat/1.0'})
        with _urlreq.urlopen(req, timeout=5) as r:
            svg_data = r.read()
        with open(cache_file, 'wb') as f:
            f.write(svg_data)
        resp = make_response(svg_data)
        resp.headers['Content-Type'] = 'image/svg+xml'
        resp.headers['Cache-Control'] = 'public, max-age=604800'
        return resp
    except Exception:
        # Fallback: rediriger vers DiceBear direct
        from flask import redirect as _redirect
        return _redirect(dicebear_url)

# ════════════════════════════════════════════════════════════
# 🕵️ SYSTÈME DE SUSPICION — Gameplay avec preuves photo
# ════════════════════════════════════════════════════════════


# �🎭 API : Récupérer la liste des avatars disponibles
@players_bp.route('/api/avatars')
def api_avatars():
    """
    Retourne la liste de tous les avatars disponibles :
    - Images PNG du dossier static/avatars
    - Emojis configurés dans avatars_config.json
    """
    from app import _dbg
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
        _dbg(f"Erreur lecture dossier avatars: {e}")
    
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
            _dbg(f"Erreur lecture config avatars: {e}")
    
    return result, 200


@players_bp.route('/test_player_selector')
def test_player_selector():
    """Page de test pour le sélecteur de joueurs"""
    return render_template('test_player_selector.html')


@players_bp.route('/api/players_points')
def api_players_points():
    """
    API pour récupérer les points de tous les joueurs de la maison en temps réel.
    Utilisé pour mettre à jour automatiquement l'affichage sans rafraîchir la page.
    """
    from app import _dbg, get_db_connection, get_house_players_points
    if 'user' not in session:
        return {'players': []}, 200
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Récupérer house_id de l'utilisateur
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'players': []}, 200
        
        house_id = row[0]
        
        # Récupérer les points de tous les joueurs avec get_house_players_points
        players = get_house_players_points(house_id)
        
        # Formater pour la réponse API
        players_data = []
        for p in players:
            players_data.append({
                'email': p['email'],
                'name': p['name'],
                'avatar': p.get('avatar'),
                'avatar_url': p.get('avatar_url'),
                'avatar_file': p.get('avatar_file'),
                'points': p['points'],
                'daily_points': p.get('daily_points', 0),
                'daily_tasks': p.get('daily_tasks', 0)
            })
        
        # Récupérer la santé de la maison
        c.execute("SELECT health FROM houses WHERE id=?", (house_id,))
        health_row = c.fetchone()
        house_health = health_row[0] if health_row and health_row[0] is not None else 100
        
        resp = jsonify({'players': players_data, 'house_health': house_health})
        resp.headers['Cache-Control'] = 'no-store'
        return resp, 200
        
    except Exception as e:
        _dbg(f"Erreur API players_points: {e}")
        return {'players': [], 'error': str(e)}, 500
    finally:
        conn.close()



