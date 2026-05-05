from flask import Blueprint, request, session, redirect, url_for, render_template, flash

customize_bp = Blueprint('customize', __name__)


@customize_bp.route('/set_bg_theme', methods=['POST'])
def set_bg_theme():
    from app import get_db_connection, BG_THEMES
    if 'user' not in session:
        return {'ok': False, 'error': 'non connecté'}, 401
    theme = request.json.get('theme', 'bleu')
    if theme not in BG_THEMES:
        return {'ok': False, 'error': 'thème invalide'}, 400
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET bg_theme=? WHERE email=?", (theme, session['user']))
        conn.commit()
        conn.close()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}, 500


@customize_bp.route('/toggle_room', methods=['POST'])
def toggle_room():
    from app import get_db_connection, _invalidate_house_cache
    if 'user' not in session:
        return {'ok': False}, 401
    data = request.get_json(force=True)
    room_key  = data.get('room_key', '')
    is_hidden = 1 if data.get('is_hidden') else 0
    if not room_key:
        return {'ok': False, 'error': 'room_key manquant'}, 400
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row:
            return {'ok': False}, 403
        house_id = row[0]
        c.execute("""
            INSERT INTO custom_rooms (house_id, room_key, is_hidden)
            VALUES (?, ?, ?)
            ON CONFLICT(house_id, room_key) DO UPDATE SET is_hidden = excluded.is_hidden
        """, (house_id, room_key, is_hidden))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}, 500
    finally:
        conn.close()
    return {'ok': True}


@customize_bp.route('/personnaliser_maison', methods=['GET', 'POST'])
def personnaliser_maison():
    from app import (get_db_connection, _dbg, _invalidate_house_cache,
                     SOCKETIO_AVAILABLE, socketio, safe_socketio_emit)
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    # Récupérer house_id depuis la DB
    house_id = None
    conn_h = get_db_connection()
    ch = conn_h.cursor()
    ch.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    row_h = ch.fetchone()
    if row_h:
        house_id = row_h[0]
    conn_h.close()

    if not house_id:
        flash("Crée ou rejoins une maison pour personnaliser les pièces ! 🏠", "info")
        return redirect(url_for('house.invite_partner'))

    # Liste complète de toutes les pièces
    ALL_ROOMS = [
        {'key': 'chambre_parentale', 'default_name': 'Chambre 1',     'image': 'images/thumbs/chambreparentale_marron.webp', 'fixed': False},
        {'key': 'chambre1',          'default_name': 'Chambre 2',     'image': 'images/thumbs/chambre1.webp',                'fixed': False},
        {'key': 'chambre2',          'default_name': 'Chambre 3',     'image': 'images/thumbs/chambre2.webp',                'fixed': False},
        {'key': 'chambre_garcon',    'default_name': 'Chambre 4',     'image': 'images/thumbs/chambre_garçon3.webp',         'fixed': False},
        {'key': 'chambre_enfant',    'default_name': 'Chambre 5',     'image': 'images/thumbs/chambre_enfant_4.webp',        'fixed': False},
        {'key': 'chambre_bebe',      'default_name': 'Chambre bébé',  'image': 'images/thumbs/chambre_bébé4_.webp',          'fixed': False},
        {'key': 'salon',             'default_name': 'Salon',         'image': 'images/thumbs/salonorange.webp',             'fixed': False},
        {'key': 'cuisine',           'default_name': 'Cuisine',       'image': 'images/thumbs/cuisinewoop.webp',             'fixed': False},
        {'key': 'salle_bain',        'default_name': 'Salle de bain', 'image': 'images/thumbs/sdbwoop.webp',                'fixed': False},
        {'key': 'toilettes',         'default_name': 'Toilettes',     'image': 'images/thumbs/Wc2.webp',                    'fixed': False},
        {'key': 'buanderie',         'default_name': 'Buanderie',     'image': 'images/thumbs/buanderie5.webp',              'fixed': False},
        {'key': 'garage',            'default_name': 'Garage',        'image': 'images/thumbs/Garage2.webp',                'fixed': False},
    ]

    if request.method == 'POST':
        conn = get_db_connection()
        c = conn.cursor()
        try:
            new_house_name = request.form.get('house_name', '').strip()
            if new_house_name:
                c.execute("UPDATE houses SET house_name=? WHERE id=?", (new_house_name, house_id))
            for room in ALL_ROOMS:
                key = room['key']
                custom_name = request.form.get(f'name_{key}', '').strip()
                is_hidden = 0 if room['fixed'] else (1 if request.form.get(f'hidden_{key}') else 0)
                if not custom_name or custom_name == room['default_name']:
                    custom_name = None
                c.execute("""
                    INSERT INTO custom_rooms (house_id, room_key, custom_name, is_hidden)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(house_id, room_key) DO UPDATE SET
                        custom_name = excluded.custom_name,
                        is_hidden   = excluded.is_hidden
                """, (house_id, key, custom_name, is_hidden))
            conn.commit()
            # 🔌 WEBSOCKET: Notifier les autres joueurs du changement de pièces/nom maison
            if SOCKETIO_AVAILABLE and socketio:
                try:
                    safe_socketio_emit('house_rooms_updated', {'house_id': house_id},
                                      namespace='/', room=f'house_{house_id}', broadcast=True)
                    _dbg(f"🔌 WebSocket: house_rooms_updated émis pour house_{house_id}")
                except Exception as ws_err:
                    _dbg(f"⚠️ Erreur WebSocket edit_house: {ws_err}")
        except Exception as e:
            conn.rollback()
            _dbg(f"⚠️ edit_house POST error: {e}")
        finally:
            conn.close()
        if request.form.get('house_name', '').strip():
            _invalidate_house_cache(session['user'])
        return redirect(url_for('customize.settings_page'))

    # GET : charger les réglages actuels
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT room_key, custom_name, is_hidden FROM custom_rooms WHERE house_id=?", (house_id,))
        custom_db = {row[0]: {'name': row[1], 'is_hidden': bool(row[2])} for row in c.fetchall()}
    except Exception:
        custom_db = {}
    finally:
        conn.close()

    rooms_data = []
    for room in ALL_ROOMS:
        r = room.copy()
        cust = custom_db.get(room['key'], {})
        r['current_name'] = cust.get('name') or room['default_name']
        r['is_hidden']    = False if room['fixed'] else cust.get('is_hidden', False)
        rooms_data.append(r)

    house_members = []
    try:
        conn_m = get_db_connection()
        cm = conn_m.cursor()
        cm.execute("SELECT name FROM users WHERE house_id=? ORDER BY id", (house_id,))
        house_members = [row[0] for row in cm.fetchall() if row[0]]
        conn_m.close()
    except Exception:
        pass

    current_house_name = ''
    try:
        conn_hn = get_db_connection()
        chn = conn_hn.cursor()
        chn.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
        hn_row = chn.fetchone()
        conn_hn.close()
        if hn_row:
            current_house_name = hn_row[0] or hn_row[1] or ''
    except Exception:
        pass

    return render_template('edit_house.html', rooms=rooms_data,
                           house_members=house_members,
                           current_house_name=current_house_name)


@customize_bp.route('/settings')
def settings_page():
    """Page réglages — regroupe gestion maison et joueurs"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template('settings.html')


@customize_bp.route('/settings/theme')
def settings_theme():
    """Page dédiée : changement de thème / couleur de fond"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template('settings_theme.html')
