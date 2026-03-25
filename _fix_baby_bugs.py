import io

# ============================================================
# FIX 1: room-baby-dot uniquement sur chambre_bébé
# ============================================================
menu_path = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html'
with io.open(menu_path, 'r', encoding='utf-8') as f:
    menu = f.read()

OLD_DOT = (
    '                                        <span class="room-baby-dot" id="room-baby-dot" title="Nouveau suivi baby" '
)

# Identifier la ligne exacte
baby_dot_line = None
for line in menu.splitlines():
    if 'room-baby-dot' in line and '<span' in line:
        baby_dot_line = line
        break

if baby_dot_line:
    print("Ligne trouvée:", repr(baby_dot_line[:120]))
    
    # La remplacer par une version conditionnelle sur chambre_bebe
    # Old: <span class="room-baby-dot" id="room-baby-dot" ... >{{ ... }}</span>
    # New: {% if room.category == 'chambre_bebe' %}<span ... >{{ ... }}</span>{% endif %}
    
    # Trouver la balise span complète
    # Elle est sur une seule ligne, donc on remplace directement
    new_line = (
        baby_dot_line.replace(
            '<span class="room-baby-dot"',
            '{% if room.category == \'chambre_bebe\' %}<span class="room-baby-dot"'
        ).rstrip()
        + '{% endif %}'
    )
    # Vérifier qu'on a bien le </span>
    if '</span>' in new_line:
        menu = menu.replace(baby_dot_line, new_line)
        print("FIX 1 appliqu\u00e9: room-baby-dot uniquement sur chambre_bebe")
    else:
        print("ERREUR: </span> pas trouv\u00e9 dans la ligne")
else:
    print("ERREUR: ligne room-baby-dot non trouv\u00e9e")

with io.open(menu_path, 'w', encoding='utf-8') as f:
    f.write(menu)

print()

# ============================================================
# FIX 2: unread_baby inclut les messages envoyés par soi-même
# (baby_tracking: on veut voir sa propre activité non encore revue)
# ============================================================
app_path = '/Users/anne-gaelledaval/Downloads/Appli web-2/app.py'
with io.open(app_path, 'r', encoding='utf-8') as f:
    app = f.read()

OLD_FUNC_SIG = "def get_unread_count_by_type(user_email, house_id, message_type, existing_conn=None):"
NEW_FUNC_SIG = "def get_unread_count_by_type(user_email, house_id, message_type, existing_conn=None, include_own=False):"

if OLD_FUNC_SIG in app:
    app = app.replace(OLD_FUNC_SIG, NEW_FUNC_SIG, 1)
    print("Signature mise \u00e0 jour")
else:
    print("ATTENTION: signature non trouv\u00e9e")

# Modifier la requete pour utiliser include_own
OLD_QUERY = '''        c.execute("""
            SELECT COUNT(*) FROM messages m
            WHERE m.house_id = ?
            AND m.message_type = ?
            AND (m.sender_email IS NULL OR m.sender_email != ?)
            AND NOT EXISTS (
                SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?
            )
        """, (house_id, message_type, user_email, user_email))
        count = c.fetchone()[0]'''

NEW_QUERY = '''        if include_own:
            c.execute("""
                SELECT COUNT(*) FROM messages m
                WHERE m.house_id = ?
                AND m.message_type = ?
                AND NOT EXISTS (
                    SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?
                )
            """, (house_id, message_type, user_email))
        else:
            c.execute("""
                SELECT COUNT(*) FROM messages m
                WHERE m.house_id = ?
                AND m.message_type = ?
                AND (m.sender_email IS NULL OR m.sender_email != ?)
                AND NOT EXISTS (
                    SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = ?
                )
            """, (house_id, message_type, user_email, user_email))
        count = c.fetchone()[0]'''

if OLD_QUERY in app:
    app = app.replace(OLD_QUERY, NEW_QUERY, 1)
    print("Requ\u00eate get_unread_count_by_type mise \u00e0 jour")
else:
    print("ERREUR: requ\u00eate non trouv\u00e9e")

# Maintenant mettre à jour les appels pour baby_tracking (include_own=True)
# 1. Dans /api/unread_counts
OLD_BABY_API = "        unread_baby = get_unread_count_by_type(session['user'], house_id, 'baby_tracking')"
NEW_BABY_API = "        unread_baby = get_unread_count_by_type(session['user'], house_id, 'baby_tracking', include_own=True)"

if OLD_BABY_API in app:
    app = app.replace(OLD_BABY_API, NEW_BABY_API, 1)
    print("Appel API unread_counts mis \u00e0 jour (include_own=True)")
else:
    print("ATTENTION: appel API baby non trouv\u00e9 - v\u00e9rifier manuellement")
    # Chercher le contexte
    idx = app.find("'baby_tracking'")
    while idx != -1:
        print("  context:", repr(app[max(0,idx-60):idx+80]))
        idx = app.find("'baby_tracking'", idx+1)

# 2. Dans la route menu (avec existing_conn)
OLD_BABY_MENU = "            unread_baby_tracking = get_unread_count_by_type(session['user'], house_id, 'baby_tracking', existing_conn=conn)"
NEW_BABY_MENU = "            unread_baby_tracking = get_unread_count_by_type(session['user'], house_id, 'baby_tracking', existing_conn=conn, include_own=True)"

if OLD_BABY_MENU in app:
    app = app.replace(OLD_BABY_MENU, NEW_BABY_MENU)
    print("Appel menu route mis \u00e0 jour (include_own=True)")
else:
    print("ATTENTION: appel menu route non trouv\u00e9")

# 3. Dans la route chambre_bebe avec current_user_name
OLD_BABY_CHAMBRE = "                    unread_baby_tracking = get_unread_count_by_type(current_user_name, house_id, 'baby_tracking', existing_conn=conn)"
NEW_BABY_CHAMBRE = "                    unread_baby_tracking = get_unread_count_by_type(current_user_name, house_id, 'baby_tracking', existing_conn=conn, include_own=True)"

if OLD_BABY_CHAMBRE in app:
    app = app.replace(OLD_BABY_CHAMBRE, NEW_BABY_CHAMBRE, 1)
    print("Appel chambre_bebe route mis \u00e0 jour (include_own=True)")
else:
    print("ATTENTION: appel chambre_bebe non trouv\u00e9 - ok si pas de double route")

with io.open(app_path, 'w', encoding='utf-8') as f:
    f.write(app)

print()
print("=> Terminé. Vérifier avec py_compile.")
