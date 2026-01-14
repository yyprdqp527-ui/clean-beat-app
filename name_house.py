
from flask import Blueprint, request, redirect, url_for, session, flash
import sqlite3
DB = "users.db"

bp = Blueprint('name_house', __name__)

@bp.route('/name_house', methods=['POST'])
def name_house():
    if 'user' not in session:
        flash("Connecte-toi pour nommer ta maison.", "warning")
        return redirect(url_for('login'))
    house_name = request.form.get('house_name', '').strip()
    if not house_name:
        flash("Le nom de la maison ne peut pas être vide.", "danger")
        return redirect(url_for('menu'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row = c.fetchone()
    if row and row[0]:
        house_id = row[0]
        c.execute("UPDATE houses SET name=?, house_name=? WHERE id=?", (house_name, house_name, house_id))
        conn.commit()
        flash("Nom de la maison mis à jour !", "success")
    conn.close()
    # Rediriger avec le paramètre welcome=1 pour afficher le message d'introduction
    return redirect(url_for('menu', welcome=1))