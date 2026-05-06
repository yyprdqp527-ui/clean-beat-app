import os
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, Response
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)

# Clé secrète admin — accessible via /admin_feedback?key=CETTE_CLE
ADMIN_FEEDBACK_KEY = os.environ.get("ADMIN_FEEDBACK_KEY", "cleanbeat_admin_2026")


@admin_bp.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """Formulaire de feedback pour les testeurs bêta"""
    from app import get_db_connection, _dbg
    if 'user' not in session:
        return redirect(url_for('auth.welcome'))

    user_email = session.get('user')
    user_name = session.get('player_name', '')

    if request.method == 'POST':
        try:
            note_globale = request.form.get('note_globale') or None
            note_facilite = request.form.get('note_facilite') or None
            note_design = request.form.get('note_design') or None
            ce_qui_plait = request.form.get('ce_qui_plait', '').strip() or None
            ce_qui_deplait = request.form.get('ce_qui_deplait', '').strip() or None
            ameliorations = request.form.get('ameliorations', '').strip() or None
            pret_a_payer = int(request.form.get('pret_a_payer', 0))
            prix_acceptable = request.form.get('prix_acceptable', '').strip() or None
            recommande_raw = request.form.get('recommande', '')
            recommande = int(recommande_raw) if recommande_raw.strip() in ('0', '1') else None
            autres_commentaires = request.form.get('autres_commentaires', '').strip() or None
            age = request.form.get('age', '').strip() or None
            situation_familiale = request.form.get('situation_familiale', '').strip() or None
            ages_enfants = request.form.get('ages_enfants', '').strip() or None
            profession = request.form.get('profession', '').strip() or None

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO beta_feedback
                    (user_email, user_name, note_globale, note_facilite, note_design,
                     ce_qui_plait, ce_qui_deplait, ameliorations,
                     pret_a_payer, prix_acceptable, recommande, autres_commentaires,
                     age, situation_familiale, ages_enfants, profession)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_email, user_name,
                int(note_globale) if note_globale else None,
                int(note_facilite) if note_facilite else None,
                int(note_design) if note_design else None,
                ce_qui_plait, ce_qui_deplait, ameliorations,
                pret_a_payer, prix_acceptable, recommande, autres_commentaires,
                age, situation_familiale, ages_enfants, profession
            ))
            conn.commit()
            conn.close()
            return render_template('feedback.html', submitted=True)
        except Exception as e:
            _dbg(f"❌ Erreur feedback: {e}")
            flash("Une erreur s'est produite. Réessaie.", "error")
            return render_template('feedback.html', submitted=False)

    return render_template('feedback.html', submitted=False)


@admin_bp.route('/admin_feedback')
def admin_feedback():
    """Page admin pour lire les feedbacks (protégée par clé URL)"""
    from app import get_db_connection
    key = request.args.get('key', '')
    if key != ADMIN_FEEDBACK_KEY:
        return "Accès refusé. Ajoute ?key=VOTRE_CLE à l'URL.", 403

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, submitted_at, user_email, user_name,
               note_globale, note_facilite, note_design,
               ce_qui_plait, ce_qui_deplait, ameliorations,
               pret_a_payer, prix_acceptable, recommande, autres_commentaires
        FROM beta_feedback
        ORDER BY submitted_at DESC
    """)
    rows = c.fetchall()
    conn.close()

    keys = ['id', 'submitted_at', 'user_email', 'user_name',
            'note_globale', 'note_facilite', 'note_design',
            'ce_qui_plait', 'ce_qui_deplait', 'ameliorations',
            'pret_a_payer', 'prix_acceptable', 'recommande', 'autres_commentaires']
    feedbacks = [dict(zip(keys, row)) for row in rows]
    return render_template('admin_feedback.html', feedbacks=feedbacks)


@admin_bp.route('/admin_feedback_csv')
def admin_feedback_csv():
    """Export CSV des feedbacks"""
    from app import get_db_connection
    import csv
    import io
    key = request.args.get('key', '')
    if key != ADMIN_FEEDBACK_KEY:
        return "Accès refusé.", 403

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM beta_feedback ORDER BY submitted_at DESC")
    rows = c.fetchall()
    col_names = [description[0] for description in c.description]
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(col_names)
    writer.writerows(rows)
    csv_content = output.getvalue()
    output.close()

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=feedbacks_cleanbeat.csv'}
    )


@admin_bp.route('/admin_clean_users')
def admin_clean_users():
    """Route debug — gestion des comptes utilisateurs"""
    from app import get_db_connection
    key = request.args.get('key', '')
    if key != 'dust2026admin':
        return "Accès refusé", 403
    action = request.args.get('action', '')
    email_keep = request.args.get('email', '').strip().lower()
    new_pwd = request.args.get('pwd', '').strip()
    conn = get_db_connection()
    c = conn.cursor()
    msg = ""
    # Action : garder uniquement un compte, supprimer tous les autres RÉELS (pas les enfants)
    if action == 'keeponly' and email_keep:
        c.execute("DELETE FROM users WHERE email != ? AND (is_child_account IS NULL OR is_child_account = 0)", (email_keep,))
        conn.commit()
        msg = f"✅ Tous les comptes adultes supprimés sauf {email_keep}"
    # Action : réinitialiser le mot de passe d'un email
    if action == 'resetpwd' and email_keep and new_pwd:
        hashed = generate_password_hash(new_pwd)
        c.execute("UPDATE users SET password=? WHERE email=?", (hashed, email_keep))
        conn.commit()
        msg = f"✅ Mot de passe réinitialisé pour {email_keep}"
    # Action : supprimer un compte par email
    if action == 'delete' and email_keep:
        c.execute("DELETE FROM users WHERE email=?", (email_keep,))
        conn.commit()
        msg = f"🗑️ Compte supprimé : {email_keep}"
    # Lister les 30 derniers comptes
    c.execute("SELECT id, email, name, registration_step, house_id FROM users ORDER BY id DESC LIMIT 30")
    rows = c.fetchall()
    conn.close()
    html = f"<h2>Comptes (30 derniers) {msg}</h2><table border=1>"
    html += "<tr><th>ID</th><th>Email</th><th>Nom</th><th>Step</th><th>House</th><th>Actions</th></tr>"
    for r in rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td>"
        html += f"<td><a href='?key=dust2026admin&action=delete&email={r[1]}' onclick=\"return confirm('Supprimer ?')\">🗑️ Supprimer</a></td></tr>"
    html += "</table>"
    html += "<br><b>⭐ Garder uniquement un compte (supprimer tous les autres) :</b><br>"
    html += "<form method=get>Email à garder: <input name=email style='width:250px'> <input type=hidden name=key value=dust2026admin> <input type=hidden name=action value=keeponly> <input type=submit value='Garder uniquement cet email' onclick=\"return confirm('Supprimer TOUS les autres comptes adultes ?')\"></form>"
    html += "<br><b>Réinitialiser un mot de passe :</b><br>"
    html += "<form method=get>Email: <input name=email style='width:250px'> Nouveau pwd: <input name=pwd> <input type=hidden name=key value=dust2026admin> <input type=hidden name=action value=resetpwd> <input type=submit value='Réinitialiser'></form>"
    return html


@admin_bp.route('/admin_beta')
def admin_beta():
    """Dashboard bêta-testeurs"""
    from app import get_db_connection
    key = request.args.get('key', '')
    if key != 'dust2026admin':
        return "Accès refusé", 403

    conn = get_db_connection()
    c = conn.cursor()
    errors = []

    # Tous les utilisateurs inscrits (hors comptes enfants)
    try:
        c.execute("""
            SELECT u.email, u.name, u.phone, u.registration_step,
                   MIN(ct.completed_at) as premiere_activite
            FROM users u
            LEFT JOIN completed_tasks ct ON ct.user_email = u.email
            WHERE u.is_child_account IS NULL OR u.is_child_account = 0
            GROUP BY u.id, u.email, u.name, u.phone, u.registration_step
            ORDER BY u.id DESC
        """)
        users_rows = c.fetchall()
    except Exception as e:
        users_rows = []
        errors.append(f"users: {e}")

    # Connexions par jour (30 derniers jours)
    try:
        c.execute("""
            SELECT DATE(logged_at) as day, COUNT(*) as cnt
            FROM login_logs
            GROUP BY DATE(logged_at)
            ORDER BY day DESC
            LIMIT 30
        """)
        daily_rows = c.fetchall()
    except Exception as e:
        daily_rows = []
        errors.append(f"login_logs jour: {e}")

    # Connexions par utilisateur (top 50)
    try:
        c.execute("""
            SELECT email, COUNT(*) as cnt, MAX(logged_at) as last_login
            FROM login_logs
            GROUP BY email
            ORDER BY cnt DESC
            LIMIT 50
        """)
        user_logins = c.fetchall()
    except Exception as e:
        user_logins = []
        errors.append(f"login_logs user: {e}")

    # Activité : tâches validées par joueur (30 derniers jours)
    try:
        c.execute("""
            SELECT user_email, COUNT(*) as nb_taches, SUM(points) as total_pts,
                   MAX(completed_at) as derniere_action
            FROM completed_tasks
            WHERE completed_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            GROUP BY user_email
            ORDER BY nb_taches DESC
            LIMIT 50
        """)
        activity_rows = c.fetchall()
    except Exception:
        try:
            c.execute("""
                SELECT user_email, COUNT(*) as nb_taches, SUM(points) as total_pts,
                       MAX(completed_at) as derniere_action
                FROM completed_tasks
                WHERE DATE(completed_at) >= DATE('now','-30 days')
                GROUP BY user_email
                ORDER BY nb_taches DESC
                LIMIT 50
            """)
            activity_rows = c.fetchall()
        except Exception as e2:
            activity_rows = []
            errors.append(f"activity: {e2}")

    # 20 dernières tâches validées (toutes personnes confondues)
    try:
        c.execute("""
            SELECT user_email, task_name, points, completed_at
            FROM completed_tasks
            ORDER BY completed_at DESC
            LIMIT 20
        """)
        recent_tasks = c.fetchall()
    except Exception as e:
        recent_tasks = []
        errors.append(f"recent_tasks: {e}")

    conn.close()

    total_users = len(users_rows)
    total_logins = sum(r[1] for r in daily_rows)
    total_tasks = sum(r[1] for r in activity_rows)

    css = """
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #e94560; } h2 { color: #0f3460; background:#16213e; padding:8px; border-radius:6px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
        th { background: #0f3460; color: #fff; padding: 8px 12px; text-align: left; }
        td { padding: 6px 12px; border-bottom: 1px solid #333; }
        tr:hover td { background: #1a2a4a; }
        .stat { display: inline-block; background: #16213e; border: 2px solid #0f3460;
                padding: 15px 25px; margin: 10px; border-radius: 10px; text-align: center; }
        .stat h3 { margin: 0; font-size: 2em; color: #e94560; }
        .stat p { margin: 5px 0 0; color: #aaa; }
        .err { background:#5a1a1a; padding:8px; border-radius:4px; margin:5px 0; font-size:0.85em; }
    </style>
    """

    html = f"{css}<h1>📊 Dashboard bêta-testeurs CleanBeat</h1>"
    if errors:
        for err in errors:
            html += f"<div class='err'>⚠️ {err}</div>"
    html += f"""
    <div>
        <div class='stat'><h3>{total_users}</h3><p>Utilisateurs inscrits</p></div>
        <div class='stat'><h3>{total_logins}</h3><p>Connexions (30j)</p></div>
        <div class='stat'><h3>{total_tasks}</h3><p>Tâches validées (30j)</p></div>
    </div>
    """

    html += "<h2>👥 Utilisateurs inscrits</h2>"
    html += "<table><tr><th>#</th><th>Email</th><th>Nom</th><th>Téléphone</th><th>1ère activité</th><th>Step</th></tr>"
    for i, r in enumerate(users_rows, 1):
        email, name, phone, step, premiere = r
        date_str = str(premiere)[:16] if premiere else '-'
        html += f"<tr><td>{i}</td><td>{email or '-'}</td><td>{name or '-'}</td><td>{phone or '-'}</td><td>{date_str}</td><td>{step or '-'}</td></tr>"
    html += "</table>"

    html += "<h2>🏃 Activité des joueurs (30 derniers jours)</h2>"
    html += "<table><tr><th>Email</th><th>Tâches validées</th><th>Points gagnés</th><th>Dernière action</th></tr>"
    for r in activity_rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{int(r[2] or 0)}</td><td>{str(r[3])[:16] if r[3] else '-'}</td></tr>"
    html += "</table>"

    html += "<h2>⚡ 20 dernières tâches validées</h2>"
    html += "<table><tr><th>Joueur</th><th>Tâche</th><th>Points</th><th>Date</th></tr>"
    for r in recent_tasks:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{str(r[3])[:16] if r[3] else '-'}</td></tr>"
    html += "</table>"

    html += "<h2>📅 Connexions par jour</h2>"
    html += "<table><tr><th>Date</th><th>Nb connexions</th></tr>"
    for r in daily_rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td></tr>"
    html += "</table>"

    html += "<h2>🔥 Connexions par utilisateur</h2>"
    html += "<table><tr><th>Email</th><th>Nb connexions</th><th>Dernière connexion</th></tr>"
    for r in user_logins:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{str(r[2])[:16] if r[2] else '-'}</td></tr>"
    html += "</table>"

    return html
