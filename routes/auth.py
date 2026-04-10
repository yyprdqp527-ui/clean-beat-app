from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/welcome')
def welcome():
    return render_template('welcome.html')


# Route de compatibilité pour templates pointant sur 'signup'
@auth_bp.route('/signup')
def signup():
    """Point d'entrée d'inscription générique (redirige vers le choix d'inscription)"""
    # Si vous préférez afficher une page de choix d'inscription, utilisez 'signup.html'
    try:
        return render_template('signup.html')
    except Exception:
        return redirect(url_for('auth.signup_email'))


# Routes de placeholder pour intégrations sociales mentionnées dans les templates
@auth_bp.route('/signup_facebook')
def signup_facebook():
    # Placeholder minimal: redirige vers l'inscription par email
    flash("Inscription via Facebook non configurée. Utilisez l'inscription par email.", "info")
    return redirect(url_for('auth.signup_email'))


@auth_bp.route('/signup_google')
def signup_google():
    # Placeholder minimal: redirige vers l'inscription par email
    flash("Inscription via Google non configurée. Utilisez l'inscription par email.", "info")
    return redirect(url_for('auth.signup_email'))


@auth_bp.route('/home')
def home():
    """Alias simple pour la page d'accueil (certaines templates utilisent 'home')."""
    return redirect(url_for('auth.welcome'))


@auth_bp.route('/signup_email', methods=['GET', 'POST'])
def signup_email():
    """Inscription avec email - ÉTAPE 1 du parcours"""
    from app import get_db_connection, _DBIntegrityError
    # Code d'invitation éventuel (joueur invité via SMS)
    invite_code = request.args.get('code', '').strip().upper() or session.get('invite_code', '')

    if request.method == 'POST':
        firstname = request.form.get('firstname', '').strip().capitalize()
        name = request.form.get('name', '').strip().capitalize()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        invite_code_form = request.form.get('invite_code', '').strip().upper()
        if invite_code_form:
            invite_code = invite_code_form

        # Validations de base
        if not firstname or not name or not email or not password:
            flash("Prénom, nom, email et mot de passe sont requis", "danger")
            return render_template('signup_email.html', invite_code=invite_code)

        if len(password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères", "danger")
            return render_template('signup_email.html', invite_code=invite_code)

        # Vérifier si email existe déjà
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT email, registration_step, password FROM users WHERE email=?", (email,))
        existing = c.fetchone()

        if existing:
            existing_step = existing[1] or ''
            existing_pw = existing[2] or ''
            # Si le compte existe mais l'inscription est incomplète (registration_step='email_signup'),
            # on autorise à reprendre / réinitialiser le compte avec les nouvelles infos
            if existing_step == 'email_signup':
                # Mettre à jour le compte incomplet avec les nouvelles données
                hashed_password = generate_password_hash(password)
                display_name = f"{firstname} {name}"
                c.execute("""
                    UPDATE users SET firstname=?, name=?, password=?, phone=?, avatar='👤'
                    WHERE email=?
                """, (firstname, display_name, hashed_password, phone, email))
                conn.commit()
                conn.close()

                session.permanent = True
                session['user'] = email
                session['user_name'] = display_name
                session['registration_step'] = 'email_signup'
                session.pop('invite_code', None)
                flash(f"Bienvenue {firstname} ! 🎉", "success")
                # Joueur principal: passer par le choix du type de foyer
                return redirect(url_for('house.choose_house_type'))
            else:
                # Compte complet → rediriger vers login
                flash("Cet email est déjà utilisé. Connecte-toi avec ton mot de passe.", "danger")
                conn.close()
                return redirect(url_for('auth.login'))

        try:
            hashed_password = generate_password_hash(password)
            display_name = f"{firstname} {name}"

            # Si joueur invité : trouver la maison du code
            house_id_to_join = None
            if invite_code:
                c.execute("SELECT id FROM houses WHERE code=?", (invite_code,))
                house_row = c.fetchone()
                if house_row:
                    house_id_to_join = house_row[0]
                else:
                    # Code invalide : on bloque l'inscription
                    flash("🚫 Code d'invitation invalide. Vérifie le lien ou contacte la personne qui t'a invité.", "danger")
                    conn.close()
                    return render_template('signup_email.html', invite_code=invite_code)

            c.execute("""
                INSERT INTO users (firstname, name, email, password, phone, points, avatar, registration_step, house_id)
                VALUES (?, ?, ?, ?, ?, 0, '👤', 'email_signup', ?)
            """, (firstname, display_name, email, hashed_password, phone, house_id_to_join))

            conn.commit()
            conn.close()

            # Sauvegarder dans la session
            session.permanent = True
            session['user'] = email
            session['user_name'] = display_name
            session['registration_step'] = 'email_signup'
            session.pop('invite_code', None)

            flash(f"Bienvenue {firstname} ! 🎉", "success")

            # Joueur invité → directement create_profile
            if house_id_to_join:
                return redirect(url_for('players.create_profile'))

            # Joueur principal: étape dédiée de choix famille/couple/coloc
            return redirect(url_for('house.choose_house_type'))

        except _DBIntegrityError:
            flash("Erreur lors de la création du compte. Réessaie.", "danger")
            conn.close()
            return render_template('signup_email.html', invite_code=invite_code)

    # GET — conserver le code d'invitation dans la session si présent
    if invite_code:
        session['invite_code'] = invite_code

    return render_template('signup_email.html', invite_code=invite_code)


@auth_bp.route('/quick_login', methods=['GET', 'POST'])
def quick_login():
    """Connexion rapide et joyeuse ! 🔑"""
    from app import get_db_connection, _log_login
    if request.method == 'GET':
        return render_template('quick_login.html')

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()

    if not email or not password:
        flash("🤔 Email et mot de passe requis !", "danger")
        return render_template('quick_login.html')

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, password FROM users WHERE email=?", (email,))
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
            conn2 = get_db_connection()
            conn2.execute("UPDATE users SET password=? WHERE email=?", (_new_hash, email))
            conn2.commit()
            conn2.close()
    conn.close()

    if user and _pwd_ok:
        session.permanent = True  # Session persistante après rafraîchissement
        session['user'] = email
        session['user_name'] = user[0]
        _log_login(email)
        flash(f"🎉 Re-bienvenue {user[0]} ! Prêt(e) pour de nouvelles aventures ? 🚀", "success")
        return redirect(url_for('menu'))
    else:
        flash("🚫 Email ou mot de passe incorrect ! Vérifie tes infos !", "danger")
        return render_template('quick_login.html')


# Login
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    from app import get_db_connection, _log_login
    # La page de login ne doit jamais être protégée par une vérification de session !
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        next_code = request.form.get('next_code', '').strip().upper() or request.args.get('next_code', '').strip().upper()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT password, registration_step, avatar, avatar_file FROM users WHERE email=?", (email,))
        user = c.fetchone()
        # Vérification robuste du mot de passe :
        # 1) check_password_hash (cas normal)
        # 2) Fallback comparaison directe (ancien compte non hashé) + re-hash auto
        _pwd_ok = False
        if user and user[0]:
            try:
                _pwd_ok = check_password_hash(user[0], password)
            except Exception:
                _pwd_ok = False
            if not _pwd_ok and user[0] == password:
                # Mot de passe stocké en clair → accepter et re-hasher
                _pwd_ok = True
                _new_hash = generate_password_hash(password)
                c.execute("UPDATE users SET password=? WHERE email=?", (_new_hash, email))
                conn.commit()
        if user and _pwd_ok:
            session.permanent = True
            session['user'] = email
            _log_login(email)

            # Si le joueur a un code d'invitation, le rattacher à la maison
            if next_code:
                c.execute("SELECT id FROM houses WHERE code=?", (next_code,))
                house_row = c.fetchone()
                if house_row:
                    c.execute("UPDATE users SET house_id=? WHERE email=?", (house_row[0], email))
                    conn.commit()
                    conn.close()
                    flash("🏠 Tu as rejoint la maison avec succès !", "success")
                    return redirect(url_for('menu'))

            conn.close()

            # Vérifier si l'utilisateur est au milieu d'une inscription non terminée
            registration_step = user[1] or ''
            avatar = user[2] or ''
            avatar_file = user[3] or ''

            # Rediriger vers create_profile seulement si l'inscription n'est pas terminée
            if registration_step == 'email_signup' and not avatar and not avatar_file:
                flash("✨ Complète ton profil pour commencer !", "info")
                return redirect(url_for('players.create_profile'))

            return redirect(url_for('menu'))
        else:
            flash("Email ou mot de passe incorrect", "danger")
            return redirect(url_for('auth.login'))
    return render_template('login.html')


# Logout
@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash("Déconnecté.", "success")
    return redirect(url_for('auth.login'))


# ─── Mot de passe oublié ────────────────────────────────────────────────────
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    from app import get_db_connection, now_paris
    reset_link = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT email FROM users WHERE email=?", (email,))
        user = c.fetchone()
        if user:
            # Supprimer les anciens tokens non utilisés pour cet email
            c.execute("DELETE FROM password_reset_tokens WHERE email=? AND used=0", (email,))
            # Générer un token sécurisé valable 1 heure
            token = secrets.token_urlsafe(32)
            expires_at = (now_paris() + timedelta(hours=1)).isoformat()
            c.execute("INSERT INTO password_reset_tokens (token, email, expires_at, used) VALUES (?, ?, ?, 0)",
                      (token, email, expires_at))
            conn.commit()
            conn.close()
            # Construire le lien (avec l'hôte actuel)
            reset_link = url_for('auth.reset_password', token=token, _external=True)
        else:
            conn.close()
            # Message neutre pour ne pas révéler si l'email existe
            reset_link = '__not_found__'
    return render_template('forgot_password.html', reset_link=reset_link)


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    from app import get_db_connection, now_paris
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT email, expires_at, used FROM password_reset_tokens WHERE token=?", (token,))
    row = c.fetchone()

    if not row:
        conn.close()
        flash("Lien invalide ou expiré.", "danger")
        return redirect(url_for('auth.login'))

    email, expires_at, used = row
    if used:
        conn.close()
        flash("Ce lien a déjà été utilisé. Fais une nouvelle demande.", "warning")
        return redirect(url_for('auth.forgot_password'))

    if now_paris() > datetime.fromisoformat(expires_at):
        conn.close()
        flash("Ce lien a expiré (valable 1h). Fais une nouvelle demande.", "warning")
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        if len(new_password) < 8:
            conn.close()
            flash("Le mot de passe doit contenir au moins 8 caractères.", "danger")
            return render_template('reset_password.html', token=token)
        # Mettre à jour le mot de passe
        hashed = generate_password_hash(new_password)
        c.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
        # Invalider le token
        c.execute("UPDATE password_reset_tokens SET used=1 WHERE token=?", (token,))
        conn.commit()
        conn.close()
        flash("✅ Mot de passe mis à jour ! Tu peux te connecter.", "success")
        return redirect(url_for('auth.login'))

    conn.close()
    return render_template('reset_password.html', token=token, email=email)
