#!/usr/bin/env python3
"""Injecte l'événement house_badge_refresh dans create_system_message et le handler dans menu.html"""
import re

# === app.py ===
with open('app.py', 'r', encoding='utf-8') as f:
    data = f.read()

# Trouver la ligne _dbg Synchronisation messagerie système
# Elle contient un emoji 🔌 (\U0001f50c) et du texte spécifique
marker = "Synchronisation messagerie syst"
idx = data.find(marker)
if idx == -1:
    print("MARKER NOT FOUND in app.py")
else:
    # Trouver la fin de la ligne _dbg
    line_end = data.find('\n', idx)
    # Vérifier qu'on n'a pas déjà injecté
    if 'house_badge_refresh' in data[idx-300:idx+200]:
        print("already injected in app.py")
    else:
        # Insérer après la ligne _dbg
        inject = (
            "\n            # Événement dédié pour rafraîchir les badges — simple et fiable\n"
            "            safe_socketio_emit('house_badge_refresh', {\n"
            "                'message_type': message_type\n"
            "            }, room=f'house_{house_id}', namespace='/', broadcast=True)"
        )
        data = data[:line_end] + inject + data[line_end:]
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(data)
        print("OK: house_badge_refresh injected in app.py")

# === menu.html ===
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    html = f.read()

if 'house_badge_refresh' in html:
    print("already injected in menu.html")
else:
    # Chercher le handler all_messages_read pour insérer avant
    target = "socket.on('all_messages_read', function(data) {"
    idx2 = html.find(target)
    if idx2 == -1:
        print("target NOT FOUND in menu.html")
    else:
        handler = (
            "// Événement dédié : rafraîchissement immédiat des badges (bébé, mission, courses)\n"
            "                        socket.on('house_badge_refresh', function(data) {\n"
            "                            refreshAllBadges();\n"
            "                            if (data.message_type === 'task_added') refreshMissionDots();\n"
            "                        });\n\n                        "
        )
        html = html[:idx2] + handler + html[idx2:]
        with open('templates/menu.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("OK: house_badge_refresh handler injected in menu.html")
