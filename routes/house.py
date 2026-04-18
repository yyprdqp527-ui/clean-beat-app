from flask import (Blueprint, request, session, redirect, url_for,
                   render_template, jsonify, flash, current_app)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

house_bp = Blueprint('house', __name__)


# ══════════════════════════════════════════════════════════════════════════
# ONBOARDING MAISON
# ══════════════════════════════════════════════════════════════════════════

@house_bp.route('/choose_house_type', methods=['GET', 'POST'])
def choose_house_type():
    """ÉTAPE 2 : Choix du type de logement"""
    if 'user' not in session:
        flash("Veuillez d'abord vous inscrire", "warning")
        return redirect(url_for('auth.signup_email'))

    if request.method == 'POST':
        house_type = request.form.get('house_type', 'family')

        # Valider le type
        if house_type not in ['family', 'couple', 'coloc']:
            house_type = 'family'

        # Sauvegarder temporairement dans la session
        session['house_type'] = house_type
        house_name_input = request.form.get('house_name', '').strip()
        if house_name_input:
            session['house_name'] = house_name_input
        session['registration_step'] = 'house_type_chosen'

        # Rediriger vers l'étape 3 : invitation partenaires
        return redirect(url_for('house.onboarding_invite'))

    return render_template('choose_house_type.html')


@house_bp.route('/onboarding_invite')
def onboarding_invite():
    """ÉTAPE 3 : Page d'explication + invitation partenaires"""
    from app import get_db_connection
    if 'user' not in session:
        flash("Veuillez d'abord vous inscrire", "warning")
        return redirect(url_for('auth.signup_email'))

    # En inscription, imposer le passage par l'étape "type de logement"
    if session.get('registration_step') == 'email_signup' and not session.get('house_type'):
        return redirect(url_for('house.choose_house_type'))

    # Récupérer ou créer le code de la maison
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()

    house_code = None
    house_id = None

    if row and row[0]:
        # L'utilisateur a déjà une maison
        house_id = row[0]
        c.execute("SELECT code FROM houses WHERE id=?", (house_id,))
        code_row = c.fetchone()
        if code_row and code_row[0]:
            house_code = code_row[0]
        else:
            # La maison existe mais n'a pas de code, on le génère
            import random
            import string
            house_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            c.execute("UPDATE houses SET code=? WHERE id=?", (house_code, house_id))
            conn.commit()

        # FIX: appliquer le nom choisi dans choose_house_type si la maison n'en a pas encore
        _session_name = session.get('house_name', '').strip()
        if _session_name:
            c.execute("SELECT name, house_name FROM houses WHERE id=?", (house_id,))
            _existing = c.fetchone()
            if _existing and (not _existing[0] or not _existing[0].strip()) and (not _existing[1] or not _existing[1].strip()):
                c.execute("UPDATE houses SET name=?, house_name=? WHERE id=?", (_session_name, _session_name, house_id))
                conn.commit()
    else:
        # Créer une nouvelle maison avec un code
        import random
        import string
        house_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        house_name = session.get('house_name', '')
        house_type = session.get('house_type', 'family')
        c.execute("INSERT INTO houses (code, name, house_name, house_type, health, last_reset_date, bg_theme) VALUES (?, ?, ?, ?, ?, date('now'), 'bleu')",
                  (house_code, house_name, house_name, house_type, 100))
        house_id = c.lastrowid
        c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, session['user']))
        conn.commit()

    conn.close()

    # Rediriger vers le flux d'invitation unifié (invite_partner_new.html)
    # Le code est dans l'URL, pas besoin de l'afficher séparément
    return redirect(url_for('house.invite_partner', source='registration'))


# ══════════════════════════════════════════════════════════════════════════
# PARAMÈTRES MAISON
# ══════════════════════════════════════════════════════════════════════════

@house_bp.route('/update_house_name', methods=['POST'])
def update_house_name():
    """Mettre à jour le nom de la maison"""
    from app import get_db_connection, _invalidate_house_cache
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'})

    try:
        new_name = request.form.get('house_name', '').strip()

        if not new_name:
            return jsonify({'success': False, 'error': 'Le nom ne peut pas être vide'})

        if len(new_name) > 50:
            return jsonify({'success': False, 'error': 'Le nom est trop long (max 50 caractères)'})

        conn = get_db_connection()
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
        _invalidate_house_cache(session['user'])
        return jsonify({'success': True, 'message': 'Nom de la maison mis à jour !'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@house_bp.route('/update_house_type', methods=['POST'])
def update_house_type():
    """Mettre à jour le type de foyer de la maison"""
    from app import get_db_connection
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'}), 401

    data = request.get_json()
    house_type = data.get('house_type', 'family')

    # Valider le type
    if house_type not in ['family', 'couple', 'coloc']:
        house_type = 'family'

    conn = get_db_connection()
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


# ══════════════════════════════════════════════════════════════════════════
# ENFANTS
# ══════════════════════════════════════════════════════════════════════════

@house_bp.route('/add_children')
def add_children():
    """Page pour ajouter des enfants (sans téléphone)"""
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('auth.login'))
    return render_template('add_children.html')


@house_bp.route('/add_child', methods=['POST'])
def add_child():
    """Créer un profil enfant sans email ni mot de passe"""
    from app import get_db_connection, _dbg, validate_avatar_file, socketio
    import time
    import os
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Non connecté'})

    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Récupérer la maison du parent
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        parent = c.fetchone()

        if not parent or not parent[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Vous devez avoir une maison'})

        house_id = parent[0]
        child_name = request.form.get('child_name', '').strip().capitalize()

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
                _dbg(f"✅ [ADD_CHILD] Avatar DiceBear: {avatar_url}")
        elif child_avatar and len(child_avatar) <= 4 and any(ord(ch) > 127 for ch in child_avatar):
            # Emoji (legacy)
            avatar = child_avatar
        elif child_photo and child_photo.filename:
            # Sauvegarder la photo (compressée)
            filename = secure_filename(child_photo.filename)
            unique_filename = f"child_{int(time.time())}_{filename}"
            # Forcer extension .jpg après compression
            unique_filename = os.path.splitext(unique_filename)[0] + '.jpg'
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            try:
                from PIL import Image, ImageOps
                img = Image.open(child_photo)
                img = ImageOps.exif_transpose(img)
                img = img.convert('RGB')
                img.thumbnail((400, 400), Image.LANCZOS)
                img.save(filepath, format='JPEG', quality=75, optimize=True)
            except ImportError:
                child_photo.save(filepath)
            avatar_file = unique_filename
        else:
            # Avatar par défaut DiceBear
            default_seed = 'baby' + str(int(time.time()))[-4:]
            child_avatar_style = 'avataaars'  # Style par défaut pour les enfants
            avatar_url = f"https://api.dicebear.com/7.x/{child_avatar_style}/svg?seed={default_seed}"
            avatar = default_seed[:8]

        # Créer un email unique pour l'enfant (interne, pas utilisé pour connexion)
        child_email = f"child_{house_id}_{int(time.time())}@cleanbeat.internal"

        # Insérer l'enfant dans la base avec le style d'avatar ET le flag is_child_account
        c.execute("""
            INSERT INTO users (email, name, avatar, avatar_file, avatar_url, avatar_style, house_id, password, is_child_account, bg_theme)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 1, 'bleu')
        """, (child_email, child_name, avatar, avatar_file, avatar_url, child_avatar_style or None, house_id))

        conn.commit()

        # 🔌 Récupérer tous les joueurs de la maison pour WebSocket (y compris les enfants)
        c.execute("""
            SELECT email, name, avatar, avatar_file, avatar_url, avatar_style, points, player_color
            FROM users
            WHERE house_id = ?
            ORDER BY name
        """, (house_id,))

        players_data = []
        for player in c.fetchall():
            player_email, player_name, player_avatar, player_avatar_file, player_avatar_url, player_avatar_style, player_points, player_color = player

            # Déterminer l'URL de l'avatar
            display_avatar_url = None
            if player_avatar_url:
                display_avatar_url = player_avatar_url
            elif validate_avatar_file(player_avatar_file):
                display_avatar_url = f"/static/avatars/{player_avatar_file}"
            elif player_avatar and player_avatar_style:
                display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style}/svg?seed={player_avatar}"
            else:
                display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style or 'adventurer'}/svg?seed={player_name or player_email}"

            players_data.append({
                'email': player_email,
                'name': player_name,
                'avatar_url': display_avatar_url,
                'points': player_points or 0,
                'color': player_color
            })

        conn.close()

        # 🔌 Émettre WebSocket pour synchroniser tous les écrans
        try:
            socketio.emit('players_list_update', {
                'players': players_data,
                'new_player': child_name,
                'action': 'child_added'
            }, namespace='/', room=f'house_{house_id}')
            _dbg(f"🔌 WebSocket: Enfant '{child_name}' ajouté (room: house_{house_id})")
        except Exception as ws_err:
            _dbg(f"⚠️ Erreur WebSocket ajout enfant: {ws_err}")

        return jsonify({'success': True, 'message': 'Enfant ajouté'})

    except Exception as e:
        from app import _dbg
        _dbg(f"[ERROR add_child] {e}")
        return jsonify({'success': False, 'error': str(e)})


# ══════════════════════════════════════════════════════════════════════════
# INVITATION / REJOINDRE
# ══════════════════════════════════════════════════════════════════════════

@house_bp.route('/invite/<code>')
def invite_welcome(code):
    """Route d'invitation personnalisée via SMS - affiche une page d'accueil chaleureuse"""
    from app import get_db_connection
    house_code = code.strip().upper()

    # Vérifier que le code existe
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, house_type FROM houses WHERE code = ?', (house_code,))
    house = c.fetchone()

    if not house:
        # Code invalide, rediriger vers la page normale
        conn.close()
        flash("Code d'invitation invalide", 'error')
        return redirect(url_for('house.join_house'))

    house_id, house_name, house_type = house

    # Trouver le créateur de la maison (premier inscrit) pour afficher son nom
    c.execute('SELECT name FROM users WHERE house_id = ? ORDER BY id ASC LIMIT 1', (house_id,))
    inviter = c.fetchone()
    inviter_name = inviter[0] if inviter else 'Ton ami'

    conn.close()

    return render_template('invite_welcome.html',
                           house_code=house_code,
                           house_name=house_name,
                           house_type=house_type,
                           inviter_name=inviter_name)


@house_bp.route('/join_house', methods=['GET', 'POST'])
def join_house():
    from app import get_db_connection, validate_avatar_file, _dbg, _log_login, socketio
    # Récupérer le code depuis l'URL (pour pré-remplir)
    code_from_url = request.args.get('code', '').strip().upper()

    if request.method == 'POST':
        house_code = request.form.get('house_code', '').strip().upper()
        user_name = request.form.get('user_name', '').strip().capitalize()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        is_login = request.form.get('is_login') == 'true'  # Nouveau champ pour distinguer connexion/inscription

        conn = get_db_connection()
        c = conn.cursor()

        # Vérifier que le code de maison existe
        c.execute("SELECT id, name FROM houses WHERE code=?", (house_code,))
        house_row = c.fetchone()

        if not house_row:
            flash("Code de maison invalide. Vérifiez le code et réessayez.", "danger")
            conn.close()
            return render_template('join_house.html', code=code_from_url)

        house_id = house_row[0]

        # MODE CONNEXION : utilisateur existant qui rejoint une nouvelle maison
        if is_login:
            if not all([house_code, email, password]):
                flash("Email et mot de passe requis pour se connecter.", "danger")
                conn.close()
                return render_template('join_house.html', code=code_from_url)

            # Vérifier les identifiants
            c.execute("SELECT email, password, name FROM users WHERE email=?", (email,))
            user = c.fetchone()

            _pwd_ok = False
            if user and user[1]:
                try:
                    _pwd_ok = check_password_hash(user[1], password)
                except Exception:
                    _pwd_ok = False
                if not _pwd_ok and user[1] == password:
                    _pwd_ok = True
                    _new_hash = generate_password_hash(password)
                    c.execute("UPDATE users SET password=? WHERE email=?", (_new_hash, email))
                    conn.commit()

            if not user or not _pwd_ok:
                flash("Email ou mot de passe incorrect.", "danger")
                conn.close()
                return render_template('join_house.html', code=code_from_url)

            # Mettre à jour la maison de l'utilisateur
            c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, email))
            conn.commit()

            # 🔌 Récupérer tous les joueurs pour WebSocket (y compris les enfants)
            c.execute("""
                SELECT email, name, avatar, avatar_file, avatar_url, avatar_style, points, player_color
                FROM users
                WHERE house_id = ?
                ORDER BY name
            """, (house_id,))

            players_data = []
            for player in c.fetchall():
                player_email, player_name, player_avatar, player_avatar_file, player_avatar_url, player_avatar_style, player_points, player_color = player

                display_avatar_url = None
                if player_avatar_url:
                    display_avatar_url = player_avatar_url
                elif validate_avatar_file(player_avatar_file):
                    display_avatar_url = f"/static/avatars/{player_avatar_file}"
                elif player_avatar and player_avatar_style:
                    display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style}/svg?seed={player_avatar}"
                else:
                    display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style or 'adventurer'}/svg?seed={player_name or player_email}"

                players_data.append({
                    'email': player_email,
                    'name': player_name,
                    'avatar_url': display_avatar_url,
                    'points': player_points or 0,
                    'color': player_color
                })

            conn.close()

            # 🔌 Émettre WebSocket
            try:
                socketio.emit('players_list_update', {
                    'players': players_data,
                    'new_player': user[2],
                    'action': 'player_joined'
                }, namespace='/', room=f'house_{house_id}')
                _dbg(f"🔌 WebSocket: Joueur '{user[2]}' a rejoint la maison (room: house_{house_id})")
            except Exception as ws_err:
                _dbg(f"⚠️ Erreur WebSocket join house: {ws_err}")

            # Connecter l'utilisateur
            session.permanent = True
            session['user'] = email
            session['name'] = user[2]
            _log_login(email)

            flash(f"🎉 Bienvenue {user[2]} ! Vous avez rejoint la maison !", "success")
            return redirect(url_for('menu') + '?nav=1')

        # MODE INSCRIPTION : nouvel utilisateur
        else:
            if not all([house_code, user_name, email, password]):
                flash("Tous les champs sont requis.", "danger")
                conn.close()
                return render_template('join_house.html', code=code_from_url)

            # Vérifier que le mot de passe fait au moins 8 caractères
            if len(password) < 8:
                flash("Le mot de passe doit contenir au moins 8 caractères.", "danger")
                conn.close()
                return render_template('join_house.html', code=code_from_url)

            try:
                # Vérifier que l'email n'existe pas déjà
                c.execute("SELECT email FROM users WHERE email=?", (email,))
                if c.fetchone():
                    flash("Cet email est déjà utilisé. Connectez-vous ou utilisez un autre email.", "danger")
                    conn.close()
                    return render_template('join_house.html', code=code_from_url)

                # Créer le nouvel utilisateur
                hashed_password = generate_password_hash(password)
                c.execute("""
                    INSERT INTO users (email, password, name, house_id, points, avatar, registration_step, bg_theme)
                    VALUES (?, ?, ?, ?, 0, '🧑', 'email_signup', 'bleu')
                """, (email, hashed_password, user_name, house_id))

                conn.commit()

                # 🔌 Récupérer tous les joueurs pour WebSocket (y compris les enfants)
                c.execute("""
                    SELECT email, name, avatar, avatar_file, avatar_url, avatar_style, points, player_color
                    FROM users
                    WHERE house_id = ?
                    ORDER BY name
                """, (house_id,))

                players_data = []
                for player in c.fetchall():
                    player_email, player_name, player_avatar, player_avatar_file, player_avatar_url, player_avatar_style, player_points, player_color = player

                    display_avatar_url = None
                    if player_avatar_url:
                        display_avatar_url = player_avatar_url
                    elif validate_avatar_file(player_avatar_file):
                        display_avatar_url = f"/static/avatars/{player_avatar_file}"
                    elif player_avatar and player_avatar_style:
                        display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style}/svg?seed={player_avatar}"
                    else:
                        display_avatar_url = f"https://api.dicebear.com/7.x/{player_avatar_style or 'adventurer'}/svg?seed={player_name or player_email}"

                    players_data.append({
                        'email': player_email,
                        'name': player_name,
                        'avatar_url': display_avatar_url,
                        'points': player_points or 0,
                        'color': player_color
                    })

                conn.close()

                # 🔌 Émettre WebSocket
                try:
                    socketio.emit('players_list_update', {
                        'players': players_data,
                        'new_player': user_name,
                        'action': 'player_registered'
                    }, namespace='/', room=f'house_{house_id}')
                    _dbg(f"🔌 WebSocket: Nouveau joueur '{user_name}' inscrit (room: house_{house_id})")
                except Exception as ws_err:
                    _dbg(f"⚠️ Erreur WebSocket registration: {ws_err}")

                # Connecter automatiquement l'utilisateur
                session.permanent = True
                session['user'] = email
                session['name'] = user_name

                flash(f"🎉 Bienvenue {user_name} ! Créez maintenant votre profil et choisissez votre avatar !", "success")
                return redirect(url_for('players.create_profile'))

            except Exception as e:
                conn.close()
                _dbg(f"Erreur lors de la création du compte: {e}")
                flash("Une erreur s'est produite. Veuillez réessayer.", "danger")
                return render_template('join_house.html', code=code_from_url)

    # GET: afficher le formulaire avec le code pré-rempli
    return render_template('join_house.html', code=code_from_url)


@house_bp.route('/invite_partner', methods=['GET', 'POST'])
def invite_partner():
    from app import get_db_connection, _dbg, send_sms_invitation
    # Vérifier si l'utilisateur est connecté
    if 'user' not in session:
        flash("Connecte-toi pour inviter des partenaires !", "warning")
        return redirect(url_for('auth.login'))

    house_code = None
    house_id = None
    house_name = None
    house_type = 'family'  # Valeur par défaut

    # Récupérer ou créer une maison pour l'utilisateur
    conn = get_db_connection()
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
        c.execute("INSERT INTO houses (code, name, health, last_reset_date, bg_theme) VALUES (?, ?, ?, date('now'), 'bleu')",
                  (house_code, '', 100))
        house_id = c.lastrowid

        # Associer l'utilisateur à cette maison
        c.execute("UPDATE users SET house_id=? WHERE email=?", (house_id, session['user']))
        conn.commit()

    elif row and row[0]:
        house_id = row[0]
        c.execute("SELECT code, house_name, name, house_type FROM houses WHERE id=?", (house_id,))
        house_row = c.fetchone()
        if house_row:
            house_code = house_row[0]
            house_name = house_row[1] if house_row[1] else house_row[2]
            house_type = house_row[3] if house_row[3] else 'family'
    conn.close()

    # Déterminer le contexte : inscription ou depuis manage_players
    source = (request.args.get('source', '') or '').strip().lower()
    posted_source = (request.form.get('invite_source', '') or '').strip().lower() if request.method == 'POST' else ''

    if source == 'manage' or posted_source == 'manage':
        session['invite_source'] = 'manage'
    elif source:
        session.pop('invite_source', None)

    from_manage = (source == 'manage' or posted_source == 'manage' or session.get('invite_source') == 'manage')

    # IMPORTANT: cette page doit rester SIMPLE par défaut.
    # Le mode "configuration maison" ne s'active que si explicitement demandé.
    from_registration = (not from_manage) and (source == 'registration' or posted_source == 'registration')

    if request.method == 'POST':
        import json

        # ─── Récupérer le nom et le type de la maison depuis le formulaire ───
        form_house_name = request.form.get('house_name', '').strip()
        if not form_house_name:
            form_house_name = 'Notre Maison'  # Valeur par défaut si vide
        form_house_type = request.form.get('house_type', 'family').strip()
        if form_house_type not in ('family', 'couple', 'coloc'):
            form_house_type = 'family'

        # Mettre à jour la maison avec le nom et le type choisis
        if house_id and form_house_name:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                "UPDATE houses SET house_name=?, name=?, house_type=? WHERE id=?",
                (form_house_name, form_house_name, form_house_type, house_id)
            )
            conn.commit()
            conn.close()
            house_name = form_house_name
            house_type = form_house_type

        partners_data = request.form.get('partners')
        children_data = request.form.get('children')

        sent_count = 0
        children_created = 0

        # Récupérer le nom de l'utilisateur actuel
        user_name = session.get('user', 'Un ami')
        if 'user' in session:
            conn = get_db_connection()
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
                for partner in partners:
                    try:
                        send_sms_invitation(
                            partner['phone'],
                            user_name,
                            house_code
                        )
                        sent_count += 1
                    except Exception as e:
                        _dbg(f"Erreur lors de l'envoi du SMS à {partner['name']}: {e}")
            except Exception as e:
                _dbg(f"Erreur lors du traitement des partenaires: {e}")

        # Traiter les enfants (création de comptes)
        if children_data and house_id:
            try:
                children = json.loads(children_data)
                conn = get_db_connection()
                c = conn.cursor()
                for child in children:
                    try:
                        import time
                        import re
                        child_name = child.get('name', '').strip()
                        child_avatar = child.get('avatar', '👶')
                        if child_name:
                            child_email = f"child_{child_name.lower().replace(' ', '_')}_{int(time.time())}@dust.local"
                            # Extraire le seed depuis l'URL DiceBear si nécessaire
                            child_avatar_url = child_avatar
                            child_avatar_seed = ''
                            child_avatar_style = 'adventurer'
                            if 'dicebear.com' in child_avatar:
                                seed_match = re.search(r'seed=([^&]+)', child_avatar)
                                style_match = re.search(r'dicebear\.com/[^/]+/([^/]+)/', child_avatar)
                                child_avatar_seed = seed_match.group(1) if seed_match else child_name.capitalize()
                                child_avatar_style = style_match.group(1) if style_match else 'adventurer'
                            else:
                                child_avatar_seed = child_avatar
                            c.execute("""
                                INSERT INTO users (email, name, house_id, points, avatar, avatar_url, avatar_style, registration_step, is_child_account, created_by, bg_theme)
                                VALUES (?, ?, ?, 0, ?, ?, ?, 'profile_created', 1, ?, 'bleu')
                            """, (child_email, child_name.capitalize(), house_id, child_avatar_seed, child_avatar_url, child_avatar_style, session.get('user', '')))
                            children_created += 1
                    except Exception as e:
                        _dbg(f"Erreur création enfant {child.get('name', '')}: {e}")
                conn.commit()
                conn.close()
            except Exception as e:
                _dbg(f"Erreur traitement enfants: {e}")

        # Messages flash
        messages = []
        if sent_count > 0:
            messages.append(f"📱 {sent_count} invitation{'s' if sent_count > 1 else ''} SMS envoyée{'s' if sent_count > 1 else ''}")
        if children_created > 0:
            messages.append(f"👶 {children_created} profil{'s' if children_created > 1 else ''} enfant{'s' if children_created > 1 else ''} créé{'s' if children_created > 1 else ''}")

        if messages:
            pass  # flash success supprimé (flux inscription silencieux)
        elif not partners_data and not children_data:
            flash("C'est parti ! Tu pourras inviter des partenaires plus tard.", "info")

        # Redirection : inscription → profil ; manage → menu
        invite_source = session.pop('invite_source', '')
        if invite_source == 'manage':
            return redirect(url_for('menu') + '?nav=1')
        elif from_registration or session.get('registration_step') == 'email_signup':
            # Vérifier si le profil est déjà complet en DB
            try:
                conn_chk = get_db_connection()
                c_chk = conn_chk.cursor()
                c_chk.execute("SELECT registration_step, name FROM users WHERE email=?", (session.get('user', ''),))
                row_chk = c_chk.fetchone()
                conn_chk.close()
                if row_chk and row_chk[0] == 'profile_created' and row_chk[1]:
                    # Profil déjà complet → aller directement au menu
                    return redirect(url_for('menu') + '?nav=1')
            except Exception:
                pass
            session['registration_step'] = 'house_named'
            return redirect(url_for('players.create_profile'))
        else:
            return redirect(url_for('menu') + '?nav=1')

    # GET : construire l'URL d'invitation
    join_url = f"{request.host_url}invite/{house_code}" if house_code else ""

    return render_template('invite_partner_new.html',
                           house_code=house_code,
                           house_name=house_name,
                           house_type=house_type,
                           join_url=join_url,
                           from_manage=from_manage,
                           from_registration=from_registration)


@house_bp.route('/partager_invitation')
def partager_invitation():
    """Page simple pour partager l'invitation avec QR Code"""
    from app import get_db_connection
    if 'user' not in session:
        flash("Connecte-toi pour inviter des partenaires !", "warning")
        return redirect(url_for('auth.login'))

    # Récupérer le code et le nom de la maison
    conn = get_db_connection()
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
        return redirect(url_for('menu') + '?nav=1')

    # Construire l'URL d'invitation
    join_url = f"{request.host_url}invite/{house_code}"

    return render_template('invitation_partner.html',
                           house_code=house_code,
                           house_name=house_name,
                           join_url=join_url)


# ══════════════════════════════════════════════════════════════════════════
# DIVERS
# ══════════════════════════════════════════════════════════════════════════

@house_bp.route('/fullhouse')
def fullhouse():
    from app import get_db_connection
    if 'user' not in session:
        flash("Connecte-toi pour accéder à cette page", "warning")
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
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
