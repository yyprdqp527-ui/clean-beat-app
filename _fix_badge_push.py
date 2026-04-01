#!/usr/bin/env python3
"""Fix 1: guard r.ok dans refreshMissionDots (menu.html)
   Fix 2: formule catégorielle pour le badge push dans /comments (app.py)"""

import re

# ── Fix 1 : refreshMissionDots ────────────────────────────────────────────────
path_menu = 'templates/menu.html'
with open(path_menu, 'r', encoding='utf-8') as f:
    menu = f.read()

old1 = (".then(function(r) { return r.json(); })\n"
        "                        .then(function(data) {\n"
        "                            if (!data || !data.rooms) return;")
new1 = (".then(function(r) { if (!r.ok) return null; return r.json(); })\n"
        "                        .then(function(data) {\n"
        "                            if (!data || !data.rooms) return;")

n1 = menu.count(old1)
print(f'[menu.html] refreshMissionDots occurrences: {n1}')
if n1 == 1:
    menu = menu.replace(old1, new1)
    with open(path_menu, 'w', encoding='utf-8') as f:
        f.write(menu)
    print('✅ Fix 1 appliqué : guard r.ok dans refreshMissionDots')
else:
    print(f'❌ Fix 1 non appliqué (occurrences={n1})')

# ── Fix 2 : badge push additive → catégoriel dans app.py ─────────────────────
path_app = 'app.py'
with open(path_app, 'r', encoding='utf-8') as f:
    app = f.read()

old2 = (
    "                        # Calculer le badge TOTAL pour l'icône accueil (messages + courses + missions + bébé)\n"
    "                        _push_badge = recipient_unread_count\n"
    "                        try:\n"
    "                            _conn_pb = get_db_connection()\n"
    "                            _cpb = _conn_pb.cursor()\n"
    '                            _cpb.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (house_id,))\n'
    "                            _push_badge += _cpb.fetchone()[0] or 0\n"
    '                            _cpb.execute("""SELECT COUNT(*) FROM custom_tasks ct WHERE ct.house_id=?\n'
    "                                AND NOT EXISTS (SELECT 1 FROM completed_tasks ctd WHERE ctd.house_id=ct.house_id\n"
    "                                AND ctd.related_task_id=ct.id)\"\"\", (house_id,))\n"
    "                            _push_badge += _cpb.fetchone()[0] or 0\n"
    "                            _conn_pb.close()\n"
    "                            _push_badge += get_unread_baby_events_count(recipient_email, house_id)\n"
    "                        except Exception:\n"
    "                            pass\n"
    "                        _push_badge = max(1, _push_badge)"
)

new2 = (
    "                        # Calculer le badge icône accueil — formule catégorielle : 1 par type présent (max 4)\n"
    "                        _courses_push = 0\n"
    "                        _missions_push = 0\n"
    "                        _baby_push = 0\n"
    "                        try:\n"
    "                            _conn_pb = get_db_connection()\n"
    "                            _cpb = _conn_pb.cursor()\n"
    '                            _cpb.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (house_id,))\n'
    "                            _courses_push = _cpb.fetchone()[0] or 0\n"
    '                            _cpb.execute("""SELECT COUNT(*) FROM custom_tasks ct WHERE ct.house_id=?\n'
    "                                AND NOT EXISTS (SELECT 1 FROM completed_tasks ctd WHERE ctd.house_id=ct.house_id\n"
    "                                AND ctd.related_task_id=ct.id)\"\"\", (house_id,))\n"
    "                            _missions_push = _cpb.fetchone()[0] or 0\n"
    "                            _conn_pb.close()\n"
    "                            _baby_push = get_unread_baby_events_count(recipient_email, house_id)\n"
    "                        except Exception:\n"
    "                            pass\n"
    "                        _push_badge = (1 if recipient_unread_count > 0 else 0) \\\n"
    "                                    + (1 if _courses_push > 0 else 0) \\\n"
    "                                    + (1 if _missions_push > 0 else 0) \\\n"
    "                                    + (1 if _baby_push > 0 else 0)\n"
    "                        _push_badge = max(1, _push_badge)"
)

n2 = app.count(old2)
print(f'[app.py] push badge additive occurrences: {n2}')
if n2 == 1:
    app = app.replace(old2, new2)
    with open(path_app, 'w', encoding='utf-8') as f:
        f.write(app)
    print('✅ Fix 2 appliqué : formule catégorielle pour badge push /comments')
else:
    print(f'❌ Fix 2 non appliqué (occurrences={n2})')
    # Affiche contexte autour pour debug
    idx = app.find("# Calculer le badge TOTAL pour l'ic")
    if idx != -1:
        print('--- contexte trouvé dans app.py ---')
        print(repr(app[idx:idx+600]))
