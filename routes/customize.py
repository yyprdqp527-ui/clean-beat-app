import os
import time
import uuid
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, current_app, jsonify
from werkzeug.utils import secure_filename

customize_bp = Blueprint('customize', __name__)

# Dossier où sont stockées les illustrations uploadées par l'utilisateur
ROOM_UPLOAD_SUBDIR = os.path.join('uploads', 'rooms')  # relatif à static/
ROOM_UPLOAD_PREFIX = 'uploads/rooms/'  # relatif à static/ → /static/uploads/rooms/
# Dimensions cibles des thumbs de pièces (matche static/images/thumbs/*.webp = 400×462)
ROOM_THUMB_W = 400
ROOM_THUMB_H = 462

# ─── Catalogue pièces personnalisées (emoji rendu en CSS côté client) ────────
# Plus aucune génération d'image serveur pour ces pièces : le menu les rend
# directement via .emoji-losange + emoji unicode (instantané).
ROOM_CATALOGUE = [
    {"key": "jardin",        "emoji": "🌿", "label": "Jardin",           "image": "images/imageqfq/Gardening11.webp"},
    {"key": "salle_billard", "emoji": "🎱", "label": "Salle de billard", "image": "images/imageqfq/ManCave65.webp"},
    {"key": "salle_tv",      "emoji": "📺", "label": "Salle TV",         "image": "images/imageqfq/ManCave76.webp"},
    {"key": "salle_sport",   "emoji": "🏋️", "label": "Salle de sport",  "image": "images/imageqfq/Gym12.webp"},
    {"key": "bureau",        "emoji": "💻", "label": "Bureau",           "image": "images/imageqfq/Writer5.webp"},
    {"key": "dressing",      "emoji": "👗", "label": "Dressing",         "image": "images/imageqfq/OrganizingCloset.webp"},
    {"key": "piscine",       "emoji": "🏊", "label": "Piscine",          "image": "images/imageqfq/Pool4.webp"},
    {"key": "terrasse",      "emoji": "🌺", "label": "Terrasse",         "image": "images/imageqfq/Furniture33.webp"},
    {"key": "animaux",       "emoji": "🐾", "label": "Animaux",          "image": "images/imageqfq/Pets9.webp"},
    {"key": "salle_lecture", "emoji": "📚", "label": "Salle lecture",    "image": "images/imageqfq/salonqfq.webp"},
]


def _legacy_emoji_to_image_b64_unused(emoji: str, size: int = 400) -> str:
    """Génère côté serveur (PIL) une image losange avec l'emoji.
    Compatible macOS (Apple Color Emoji) et Linux (NotoColorEmoji si installé).
    Utilisé par pregenerate_emoji_cache() au démarrage."""
    import base64
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Tenter de charger une police emoji couleur (macOS / Linux)
    font = None
    for fp in [
        '/System/Library/Fonts/Apple Color Emoji.ttc',           # macOS
        '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',      # Debian/Ubuntu
        '/usr/share/fonts/noto-emoji/NotoColorEmoji.ttf',         # Red Hat
    ]:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, size=int(size * 0.55))
                break
            except Exception:
                pass

    if font:
        try:
            bbox = draw.textbbox((0, 0), emoji, font=font, embedded_color=True)
            x = (size - (bbox[2] - bbox[0])) // 2 - bbox[0]
            y = (size - (bbox[3] - bbox[1])) // 2 - bbox[1]
            draw.text((x, y), emoji, font=font, embedded_color=True)
        except Exception:
            pass  # police présente mais rendu impossible → fond blanc conservé

    # Masque losange (identique à _save_emoji_dataurl)
    mask_l = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask_l).polygon(
        [(size // 2, 4), (size - 4, size // 2), (size // 2, size - 4), (4, size // 2)],
        fill=255
    )
    clipped = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    clipped.paste(img, mask=mask_l)
    img = clipped

    # Overlay glassmorphism (identique à _save_emoji_dataurl)
    overlay = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw_o = ImageDraw.Draw(overlay)
    draw_o.polygon(
        [(size // 2, 8), (size - 8, size // 2), (size // 2, size - 8), (8, size // 2)],
        outline=(255, 255, 255, 160), width=4
    )
    draw_o.polygon(
        [(size // 2, 10), (size - 22, size // 2 - 18), (size // 2, size // 2 - 8), (22, size // 2 - 18)],
        fill=(255, 255, 255, 40)
    )
    img = Image.alpha_composite(img, overlay)

    # Toile 400×462 (matche les thumbs existants)
    canvas = Image.new('RGBA', (ROOM_THUMB_W, ROOM_THUMB_H), (0, 0, 0, 0))
    canvas.paste(img, (0, (ROOM_THUMB_H - size) // 2), img)
    img = canvas

    buf = BytesIO()
    img.save(buf, 'WEBP', quality=88, method=6)
    buf.seek(0)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')


def pregenerate_emoji_cache():
    """No-op conservé pour compatibilité d'import.
    Le rendu emoji est désormais fait en CSS côté client — aucune génération
    d'image serveur n'est nécessaire.
    """
    pass


def _is_user_uploaded_image(path):
    """Autorise uniquement les paths static/uploads/rooms/<fichier>."""
    if not isinstance(path, str):
        return False
    if not path.startswith(ROOM_UPLOAD_PREFIX):
        return False
    # Pas de remontée de dossier
    rest = path[len(ROOM_UPLOAD_PREFIX):]
    if '/' in rest or '\\' in rest or '..' in rest or not rest:
        return False
    return True

# Liste blanche des illustrations disponibles pour les pièces personnalisées
# (uniquement des thumbs isométriques déjà présents dans /static/images/thumbs/)
AVAILABLE_ROOM_IMAGES = [
    {'file': 'images/thumbs/salonorange.webp',          'label': 'Salon'},
    {'file': 'images/thumbs/cuisinewoop.webp',          'label': 'Cuisine'},
    {'file': 'images/thumbs/sdbwoop.webp',              'label': 'Salle de bain'},
    {'file': 'images/imageqfq/toilet2.webp',                  'label': 'Toilettes'},
    {'file': 'images/thumbs/buanderie5.webp',           'label': 'Buanderie'},
    {'file': 'images/thumbs/Garage2.webp',              'label': 'Garage'},
    {'file': 'images/thumbs/bureau.webp',               'label': 'Bureau'},
    {'file': 'images/thumbs/chambreparentale_marron.webp','label': 'Chambre'},
    {'file': 'images/imageqfq/Furniture28.webp',             'label': 'Chambre 2'},
    {'file': 'images/imageqfq/litados.webp',             'label': 'Chambre 3'},
    {'file': 'images/imageqfq/it.webp',      'label': 'Chambre garçon'},
    {'file': 'images/imageqfq/Furniture64.webp',     'label': 'Chambre enfant'},
    {'file': 'images/imageqfq/GreenBaby58.webp',       'label': 'Chambre bébé'},
    {'file': 'images/thumbs/default.webp',              'label': 'Autre'},
    {'file': 'images/imageqfq/Gardening11.webp',         'label': 'Jardin'},
    {'file': 'images/imageqfq/ManCave65.webp',           'label': 'Salle de billard'},
    {'file': 'images/imageqfq/ManCave76.webp',           'label': 'Salle TV'},
    {'file': 'images/imageqfq/Gym12.webp',               'label': 'Salle de sport'},
    {'file': 'images/imageqfq/Writer5.webp',             'label': 'Bureau'},
    {'file': 'images/imageqfq/OrganizingCloset.webp',    'label': 'Dressing'},
    {'file': 'images/imageqfq/Pool4.webp',               'label': 'Piscine'},
    {'file': 'images/imageqfq/Furniture33.webp',         'label': 'Terrasse'},
    {'file': 'images/imageqfq/Pets9.webp',               'label': 'Animaux'},
    {'file': 'images/imageqfq/salonqfq.webp',            'label': 'Salle lecture'},
]
_ALLOWED_IMAGE_FILES = {img['file'] for img in AVAILABLE_ROOM_IMAGES}


def _is_valid_room_image(path):
    """Une image valide pour une pièce custom est soit dans la liste blanche,
       soit dans le dossier des uploads utilisateur."""
    return (path in _ALLOWED_IMAGE_FILES) or _is_user_uploaded_image(path)


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


@customize_bp.route('/rename_room', methods=['POST'])
def rename_room():
    """Renomme une pièce (standard ou custom). Si new_name vide, retire le nom personnalisé."""
    from app import get_db_connection, safe_socketio_emit, SOCKETIO_AVAILABLE, socketio, _dbg
    if 'user' not in session:
        return {'ok': False}, 401
    data = request.get_json(force=True)
    room_key = (data.get('room_key') or '').strip()
    new_name = (data.get('new_name') or '').strip()
    if not room_key:
        return {'ok': False, 'error': 'room_key manquant'}, 400
    # Limite de longueur raisonnable
    new_name = new_name[:60]
    custom_name = new_name or None
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        row = c.fetchone()
        if not row:
            return {'ok': False}, 403
        house_id = row[0]
        c.execute("""
            INSERT INTO custom_rooms (house_id, room_key, custom_name)
            VALUES (?, ?, ?)
            ON CONFLICT(house_id, room_key) DO UPDATE SET custom_name = excluded.custom_name
        """, (house_id, room_key, custom_name))
        conn.commit()
        # WebSocket : notifier les autres joueurs
        if SOCKETIO_AVAILABLE and socketio:
            try:
                safe_socketio_emit('house_rooms_updated', {'house_id': house_id},
                                   namespace='/', room=f'house_{house_id}', broadcast=True)
            except Exception as ws_err:
                _dbg(f"⚠️ Erreur WebSocket rename_room: {ws_err}")
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}, 500
    finally:
        conn.close()
    return {'ok': True, 'custom_name': custom_name}


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
        {'key': 'chambre_parentale', 'default_name': 'Chambre 1',     'image': 'images/imageqfq/litparent.webp', 'fixed': False},
        {'key': 'chambre1',          'default_name': 'Chambre 2',     'image': 'images/imageqfq/Furniture28.webp',                'fixed': False},
        {'key': 'chambre2',          'default_name': 'Chambre 3',     'image': 'images/imageqfq/litados.webp',                'fixed': False},
        {'key': 'chambre_garcon',    'default_name': 'Chambre 4',     'image': 'images/imageqfq/it.webp',         'fixed': False},
        {'key': 'chambre_enfant',    'default_name': 'Chambre 5',     'image': 'images/imageqfq/Furniture64.webp',        'fixed': False},
        {'key': 'chambre_bebe',      'default_name': 'Chambre bébé',  'image': 'images/imageqfq/GreenBaby58.webp',          'fixed': False},
        {'key': 'salon',             'default_name': 'Salon',         'image': 'images/imageqfq/FurnitureClipart68.webp',             'fixed': False},
        {'key': 'cuisine',           'default_name': 'Cuisine',       'image': 'images/imageqfq/OvenStove.webp',             'fixed': False},
        {'key': 'salle_bain',        'default_name': 'Salle de bain', 'image': 'images/imageqfq/bathtub.webp',                'fixed': False},
        {'key': 'toilettes',         'default_name': 'Toilettes',     'image': 'images/imageqfq/toilet2.webp',                    'fixed': False},
        {'key': 'buanderie',         'default_name': 'Buanderie',     'image': 'images/imageqfq/Laundry_basket.webp',              'fixed': False},
        {'key': 'garage',            'default_name': 'Garage',        'image': 'images/imageqfq/voiture.wepb.webp',                'fixed': False},
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
                is_hidden = 1 if request.form.get(f'hidden_{key}') else 0
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
                # ⚠️ Si la pièce vient d'être ajoutée par AJAX juste avant le submit,
                # le formulaire HTML ne contient PAS encore les champs name_/hidden_
                # pour cette clé. On skip pour éviter d'écraser custom_name avec NULL.
                raw_name = request.form.get(f'name_{key}', None)
                raw_hidden = request.form.get(f'hidden_{key}', None)
                if raw_name is None and raw_hidden is None:
                    continue
                custom_name = (raw_name or '').strip() or None
                is_hidden = 1 if raw_hidden else 0
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
        c.execute("SELECT room_key, custom_name, custom_image, is_hidden, emoji, image_data FROM custom_rooms WHERE house_id=?", (house_id,))
        custom_db = {row[0]: {'name': row[1], 'image': row[2], 'is_hidden': bool(row[3]), 'emoji': row[4], 'image_data': row[5]} for row in c.fetchall()}
    except Exception:
        custom_db = {}
    finally:
        conn.close()

    rooms_data = []
    for room in ALL_ROOMS:
        r = room.copy()
        cust = custom_db.get(room['key'], {})
        r['current_name'] = cust.get('name') or room['default_name']
        r['is_hidden']    = cust.get('is_hidden', False)
        rooms_data.append(r)

    # 🆕 Pièces personnalisées (room_key commence par 'custom_')
    extra_rooms_data = []
    for key, cust in custom_db.items():
        if not key.startswith('custom_'):
            continue
        emoji = cust.get('emoji') or None
        image_data = cust.get('image_data') or None
        img = cust.get('image') or ''
        # Sécurité : autoriser uniquement liste blanche OU upload utilisateur
        if img and not _is_valid_room_image(img):
            img = 'images/thumbs/default.webp'
        if not emoji and not image_data and not img:
            img = 'images/thumbs/default.webp'
        extra_rooms_data.append({
            'key': key,
            'image': img,
            'emoji': emoji,
            'image_data': image_data,
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


def _save_emoji_dataurl(data_url, app, size=400):
    """Décode un data URL (image PNG/WEBP générée côté navigateur via Canvas),
    applique un masque losange net, sauvegarde en WEBP. Retourne le chemin relatif
    static/ ou None en cas d'échec.
    Le rendu de l'emoji est fait par le navigateur (qui sait toujours afficher
    les emojis couleur) — PIL ne sert qu'à appliquer le masque + sauvegarder."""
    try:
        if not isinstance(data_url, str):
            return None
        import re, base64
        m = re.match(r'^data:image/(?:png|webp);base64,(.+)$', data_url)
        if not m:
            return None
        b64 = m.group(1)
        # Limite anti-DoS : ~500 KB max (~375 KB raw)
        if len(b64) > 500_000:
            return None
        raw = base64.b64decode(b64, validate=True)
        from io import BytesIO
        from PIL import Image, ImageDraw
        img = Image.open(BytesIO(raw)).convert('RGBA')
        if img.size != (size, size):
            img = img.resize((size, size), Image.LANCZOS)

        # Masque losange : coords EXACTEMENT identiques au Canvas JS (inset 4px)
        # ⚠️ Ne pas utiliser putalpha() : les pixels canvas hors-losange ont RGB=(0,0,0)
        # et seraient forcés opaques noirs. On utilise paste() qui préserve l'alpha original.
        mask_l = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask_l).polygon(
            [(size // 2, 4), (size - 4, size // 2), (size // 2, size - 4), (4, size // 2)],
            fill=255
        )
        clipped = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        clipped.paste(img, mask=mask_l)
        img = clipped

        # Overlay glassmorphism : contour blanc + reflet haut (effet verre)
        overlay = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw_o = ImageDraw.Draw(overlay)
        draw_o.polygon([
            (size // 2, 8),
            (size - 8, size // 2),
            (size // 2, size - 8),
            (8, size // 2),
        ], outline=(255, 255, 255, 160), width=4)
        draw_o.polygon([
            (size // 2, 10),
            (size - 22, size // 2 - 18),
            (size // 2, size // 2 - 8),
            (22, size // 2 - 18),
        ], fill=(255, 255, 255, 40))
        img = Image.alpha_composite(img, overlay)

        # Expansion à 400×462 pour correspondre aux dimensions des thumbs par défaut
        canvas = Image.new('RGBA', (ROOM_THUMB_W, ROOM_THUMB_H), (0, 0, 0, 0))
        canvas.paste(img, (0, (ROOM_THUMB_H - size) // 2), img)
        img = canvas

        # Retourner le data:URL base64 WEBP (compatible Render — filesystem éphémère)
        buf = BytesIO()
        img.save(buf, 'WEBP', quality=88, method=6)
        b64_out = base64.b64encode(buf.getvalue()).decode('ascii')
        return f"data:image/webp;base64,{b64_out}"
        # # Sauvegarde sur disque (désactivée — fichiers perdus à chaque redéploiement sur Render)
        # dest_dir = os.path.join(app.static_folder, ROOM_UPLOAD_SUBDIR)
        # os.makedirs(dest_dir, exist_ok=True)
        # filename = f"emoji_{uuid.uuid4().hex[:12]}.webp"
        # filepath = os.path.join(dest_dir, filename)
        # img.save(filepath, 'WEBP', quality=88, method=6)
        # return f"{ROOM_UPLOAD_PREFIX}{filename}"
    except Exception as e:
        print(f"⚠️ _save_emoji_dataurl error: {e}", flush=True)
        return None


@customize_bp.route('/add_custom_room', methods=['POST'])
def add_custom_room():
    from app import get_db_connection, _invalidate_house_cache
    if 'user' not in session:
        return {'ok': False, 'error': 'non connecté'}, 401
    data = request.get_json(silent=True) or {}
    name  = (data.get('name') or '').strip()
    image = (data.get('image') or '').strip()
    image_data_url = data.get('image_data_url') or ''
    image_b64 = ''
    if not name:
        return {'ok': False, 'error': 'nom manquant'}, 400
    if len(name) > 30:
        name = name[:30]
    if not _is_valid_room_image(image):
        if image_data_url:
            saved = _save_emoji_dataurl(image_data_url, current_app._get_current_object())
            if saved and saved.startswith('data:'):
                # Stocker le data:URL dans image_data (persiste en DB, pas sur disque)
                image_b64 = saved
                image = ''
            else:
                image = saved or 'images/thumbs/default.webp'
        else:
            image = ''

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
        emoji = (data.get('emoji') or '').strip()
        c.execute("""
            INSERT INTO custom_rooms (house_id, room_key, custom_name, custom_image, is_hidden, emoji, image_data)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """, (house_id, room_key, name, image, emoji, image_b64))
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
        # Bloquer si des tâches non validées existent pour cette pièce
        c.execute("""
            SELECT COUNT(*) FROM custom_tasks ct
            WHERE ct.house_id = ? AND ct.category = ?
            AND NOT EXISTS (
                SELECT 1 FROM completed_tasks ctd
                WHERE ctd.house_id = ct.house_id
                AND ctd.category = ct.category
                AND ctd.task_name = ct.task_name
            )
        """, (house_id, room_key))
        pending = c.fetchone()[0]
        if pending > 0:
            return jsonify({'ok': False, 'error': 'pending_tasks', 'count': pending}), 400
        c.execute("DELETE FROM custom_rooms WHERE house_id=? AND room_key=?", (house_id, room_key))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}, 500
    finally:
        conn.close()
    return {'ok': True}


@customize_bp.route('/upload_room_image', methods=['POST'])
def upload_room_image():
    """Upload d'une photo (caméra ou galerie) à utiliser comme illustration de
       pièce personnalisée. Retourne le chemin relatif (à utiliser ensuite
       comme valeur du champ `image` dans /add_custom_room)."""
    if 'user' not in session:
        return {'ok': False, 'error': 'non connecté'}, 401

    photo = request.files.get('photo')
    if not photo or not photo.filename:
        return {'ok': False, 'error': 'aucun fichier'}, 400

    # Limite simple côté serveur (~5 Mo) après lecture
    try:
        photo.seek(0, 2)
        size = photo.tell()
        photo.seek(0)
        if size > 5 * 1024 * 1024:
            return {'ok': False, 'error': 'image trop lourde (max 5 Mo)'}, 400
    except Exception:
        pass

    # Préparer le dossier de destination static/uploads/rooms/
    static_root = os.path.join(current_app.root_path, 'static')
    dest_dir = os.path.join(static_root, ROOM_UPLOAD_SUBDIR)
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except Exception as e:
        return {'ok': False, 'error': f'mkdir: {e}'}, 500

    base = secure_filename(photo.filename) or 'room.jpg'
    ext = os.path.splitext(base)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.heic'):
        ext = '.jpg'
    unique = f"room_{uuid.uuid4().hex[:12]}.webp"  # WEBP transparent (match thumbs isométriques)
    filepath = os.path.join(dest_dir, unique)

    try:
        from PIL import Image, ImageOps, ImageDraw
        img = Image.open(photo)
        img = ImageOps.exif_transpose(img)
        img = img.convert('RGBA')
        # Crop centré carré, puis resize 256x256 pour matcher les thumbs isométriques
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        # Crop cover centré sur 400×462 (remplit le cadre entier)
        target_w, target_h = ROOM_THUMB_W, ROOM_THUMB_H
        ratio = max(target_w / w, target_h / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left2 = (new_w - target_w) // 2
        top2  = (new_h - target_h) // 2
        img = img.crop((left2, top2, left2 + target_w, top2 + target_h))
        img = img.convert('RGB')

        img.save(filepath, format='WEBP', quality=88, method=6)
        from io import BytesIO as _BytesIO
        import base64 as _base64
        _buf = _BytesIO()
        img.save(_buf, format='WEBP', quality=88, method=6)
        _buf.seek(0)
        img_b64 = "data:image/webp;base64," + _base64.b64encode(_buf.getvalue()).decode('utf-8')
    except ImportError:
        photo.save(filepath)
        img_b64 = ''
    except Exception as e:
        return {'ok': False, 'error': f'image: {e}'}, 500

    rel_path = f"{ROOM_UPLOAD_PREFIX}{unique}"

    # Lire le nom de pièce (envoyé dans le FormData avec la photo)
    custom_name = (request.form.get('room_name') or request.form.get('custom_name') or '').strip()
    if not custom_name:
        return {'ok': False, 'error': 'Nom de pièce manquant'}, 400
    if len(custom_name) > 30:
        custom_name = custom_name[:30]

    # Créer la pièce directement en DB
    room_key = None
    try:
        from app import get_db_connection as _get_db, _invalidate_house_cache as _inval
        _conn = _get_db()
        _c = _conn.cursor()
        _c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
        _urow = _c.fetchone()
        if not _urow or not _urow[0]:
            _conn.close()
            return {'ok': False, 'error': 'pas de maison'}, 403
        room_key = f"custom_{int(time.time() * 1000)}"
        _c.execute("""
            INSERT INTO custom_rooms (house_id, room_key, custom_name, custom_image, is_hidden, image_data)
            VALUES (?, ?, ?, ?, 0, ?)
        """, (_urow[0], room_key, custom_name, rel_path, img_b64))
        _conn.commit()
        try:
            _inval(_urow[0])
        except Exception:
            pass
    except Exception as _db_err:
        print(f"⚠️ upload_room_image DB error: {_db_err}", flush=True)
        try:
            _conn.rollback()
        except Exception:
            pass
        return {'ok': False, 'error': 'Erreur base de données'}, 500
    finally:
        try:
            _conn.close()
        except Exception:
            pass

    return {'ok': True, 'image': rel_path, 'image_b64': img_b64, 'room_key': room_key, 'name': custom_name}


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
