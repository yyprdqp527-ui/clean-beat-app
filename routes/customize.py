import time
from flask import Blueprint, request, session, redirect, url_for, render_template, flash

customize_bp = Blueprint('customize', __name__)

# Liste blanche des illustrations disponibles pour les pièces personnalisées
# (uniquement des thumbs isométriques déjà présents dans /static/images/thumbs/)
AVAILABLE_ROOM_IMAGES = [
    {'file': 'images/thumbs/salonorange.webp',          'label': 'Salon'},
    {'file': 'images/thumbs/cuisinewoop.webp',          'label': 'Cuisine'},
    {'file': 'images/thumbs/sdbwoop.webp',              'label': 'Salle de bain'},
    {'file': 'images/thumbs/Wc2.webp',                  'label': 'Toilettes'},
    {'file': 'images/thumbs/buanderie5.webp',           'label': 'Buanderie'},
    {'file': 'images/thumbs/Garage2.webp',              'label': 'Garage'},
    {'file': 'images/thumbs/bureau.webp',               'label': 'Bureau'},
    {'file': 'images/thumbs/chambreparentale_marron.webp','label': 'Chambre'},
    {'file': 'images/thumbs/chambre1.webp',             'label': 'Chambre 2'},
    {'file': 'images/thumbs/chambre2.webp',             'label': 'Chambre 3'},
    {'file': 'images/thumbs/chambre_garçon3.webp',      'label': 'Chambre garçon'},
    {'file': 'images/thumbs/chambre_enfant_4.webp',     'label': 'Chambre enfant'},
    {'file': 'images/thumbs/chambre_bébé4_.webp',       'label': 'Chambre bébé'},
    {'file': 'images/thumbs/default.webp',              'label': 'Autre'},
]
_ALLOWED_IMAGE_FILES = {img['file'] for img in AVAILABLE_ROOM_IMAGES}


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

            # 🆕 Pièces personnalisées (room_key commence par 'custom_')
            #    Récupère la liste actuelle pour mettre à jour leur nom + état masqué.
            try:
                c.execute(
                    "SELECT room_key FROM custom_rooms WHERE house_id=? AND room_key LIKE 'custom_%'",
                    (house_id,)
                )
                extra_keys = [r[0] for r in c.fetchall()]
            except Exception:
                extra_keys = []
            for key in extra_keys:
                custom_name = request.form.get(f'name_{key}', '').strip() or None
                is_hidden = 1 if request.form.get(f'hidden_{key}') else 0
                c.execute("""
                    UPDATE custom_rooms
                    SET custom_name = ?, is_hidden = ?
                    WHERE house_id = ? AND room_key = ?
                """, (custom_name, is_hidden, house_id, key))
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
        c.execute("SELECT room_key, custom_name, custom_image, is_hidden FROM custom_rooms WHERE house_id=?", (house_id,))
        custom_db = {row[0]: {'name': row[1], 'image': row[2], 'is_hidden': bool(row[3])} for row in c.fetchall()}
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

    # 🆕 Pièces personnalisées (room_key commence par 'custom_')
    extra_rooms_data = []
    for key, cust in custom_db.items():
        if not key.startswith('custom_'):
            continue
        img = cust.get('image') or 'images/thumbs/default.webp'
        # Sécurité : n'utiliser que des images de la liste blanche
        if img not in _ALLOWED_IMAGE_FILES:
            img = 'images/thumbs/default.webp'
        extra_rooms_data.append({
            'key': key,
            'image': img,
            'current_name': cust.get('name') or 'Pièce personnalisée',
            'is_hidden': cust.get('is_hidden', False),
        })
    extra_rooms_data.sort(key=lambda r: r['key'])

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
                           extra_rooms=extra_rooms_data,
                           available_images=AVAILABLE_ROOM_IMAGES,
                           house_members=house_members,
                           current_house_name=current_house_name)


@customize_bp.route('/add_custom_room', methods=['POST'])
def add_custom_room():
    """Ajoute une pièce personnalisée à la maison de l'utilisateur."""
    from app import get_db_connection, _invalidate_house_cache
    if 'user' not in session:
        return {'ok': False, 'error': 'non connecté'}, 401
    data = request.get_json(silent=True) or {}
    name  = (data.get('name') or '').strip()
    image = (data.get('image') or '').strip()
    if not name:
        return {'ok': False, 'error': 'nom manquant'}, 400
    if len(name) > 30:
        name = name[:30]
    if image not in _ALLOWED_IMAGE_FILES:
        image = 'images/thumbs/default.webp'

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'ok': False, 'error': 'pas de maison'}, 403
        house_id = row[0]
        # Génère une clé unique : custom_<timestamp_ms>
        room_key = f"custom_{int(time.time() * 1000)}"
        c.execute("""
            INSERT INTO custom_rooms (house_id, room_key, custom_name, custom_image, is_hidden)
            VALUES (?, ?, ?, ?, 0)
        """, (house_id, room_key, name, image))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}, 500
    finally:
        conn.close()
    return {'ok': True, 'room_key': room_key, 'name': name, 'image': image}


@customize_bp.route('/delete_custom_room', methods=['POST'])
def delete_custom_room():
    """Supprime une pièce personnalisée (uniquement les room_key 'custom_*')."""
    from app import get_db_connection
    if 'user' not in session:
        return {'ok': False, 'error': 'non connecté'}, 401
    data = request.get_json(silent=True) or {}
    room_key = (data.get('room_key') or '').strip()
    if not room_key.startswith('custom_'):
        return {'ok': False, 'error': 'clé invalide'}, 400

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row or not row[0]:
            return {'ok': False, 'error': 'pas de maison'}, 403
        house_id = row[0]
        c.execute("DELETE FROM custom_rooms WHERE house_id=? AND room_key=?", (house_id, room_key))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}, 500
    finally:
        conn.close()
    return {'ok': True}


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
