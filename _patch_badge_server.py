#!/usr/bin/env python3
"""Retire courses+missions du badge push serveur dans app.py"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# -------------------------------------------------------------------
# 1. notify_house_members : calcul total badge
# -------------------------------------------------------------------
old1 = (
    "                # Badge icône : compter par TYPE (1 par catégorie présente, max 4)\n"
    "                # Évite d'afficher \"7\" quand il y a 3 missions + 2 courses + 1 message + 1 bébé\n"
    "                msgs = get_unread_message_count(user_email, house_id)\n"
    "                baby = get_unread_baby_events_count(user_email, house_id)\n"
    "                total = (\n"
    "                    (1 if msgs > 0 else 0) +\n"
    "                    (1 if baby > 0 else 0) +\n"
    "                    (1 if pending_missions > 0 else 0) +\n"
    "                    (1 if courses_pending > 0 else 0)\n"
    "                )\n"
    "                personalized_data['badge'] = max(1, total)"
)
new1 = (
    "                # Badge icone : seulement messages + bebe non lus\n"
    "                # courses et missions EXCLUS (taches en attente, pas des notifs nouvelles)\n"
    "                msgs = get_unread_message_count(user_email, house_id)\n"
    "                baby = get_unread_baby_events_count(user_email, house_id)\n"
    "                total = (\n"
    "                    (1 if msgs > 0 else 0) +\n"
    "                    (1 if baby > 0 else 0)\n"
    "                )\n"
    "                personalized_data['badge'] = max(1, total) if total > 0 else 1"
)

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("OK: notify_house_members badge corrige")
else:
    print("SKIP: section 1 non trouvee")

# -------------------------------------------------------------------
# 2. send_message push : _push_badge
# -------------------------------------------------------------------
old2 = (
    "                        _push_badge = (1 if recipient_unread_count > 0 else 0) \\\n"
    "                                    + (1 if _courses_push > 0 else 0) \\\n"
    "                                    + (1 if _missions_push > 0 else 0) \\\n"
    "                                    + (1 if _baby_push > 0 else 0)\n"
    "                        _push_badge = max(1, _push_badge)"
)
new2 = (
    "                        # Badge : seulement messages + bebe (pas courses/missions)\n"
    "                        _push_badge = (1 if recipient_unread_count > 0 else 0) \\\n"
    "                                    + (1 if _baby_push > 0 else 0)\n"
    "                        _push_badge = max(1, _push_badge)"
)

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("OK: send_message badge corrige")
else:
    print("SKIP: section 2 non trouvee")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Sauvegarde OK")
