#!/usr/bin/env python3
"""
Fix 1 (app.py) : save_baby_tracking -> create_system_message (push + WebSocket)
Fix 2 (menu.html) : ajouter handlers socket.on reminder_added / reminder_toggle
"""
import sys

# ══════════════════════════════════════════════════════════════════
# FIX 1 — app.py : save_baby_tracking
# ══════════════════════════════════════════════════════════════════
path_app = 'app.py'
with open(path_app, encoding='utf-8') as f:
    app = f.read()

OLD_BABY = (
    "    # Envoyer le message directement dans la base de données\n"
    "    try:\n"
    "        from datetime import datetime\n"
    "        conn = get_db_connection()\n"
    "        c = conn.cursor()\n"
    "        \n"
    "        c.execute(\"\"\"\n"
    "            INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, timestamp)\n"
    "            VALUES (?, ?, 'house', ?, 'baby_tracking', ?)\n"
    "        \"\"\", (house_id, session['user'], message_text, datetime.now().isoformat()))\n"
    "        \n"
    "        message_id = c.lastrowid\n"
    "        conn.commit()\n"
    "        conn.close()\n"
    "        \n"
    "        _dbg(f\"\u2705 Message baby_tracking cr\u00e9\u00e9 avec ID: {message_id} pour {user_name}\")\n"
    "        \n"
    "        # \u2705 IMPORTANT : Marquer automatiquement comme \"lu\" pour l'auteur de l'action\n"
    "        # L'auteur ne doit PAS voir de notification pour sa propre action\n"
    "        mark_message_as_read(message_id, session['user'])\n"
    "        _dbg(f\"\u2705 Message baby_tracking ID {message_id} marqu\u00e9 comme lu pour l'auteur {session['user']}\")\n"
    "        \n"
    "        # \ud83d\udd0c Synchroniser la liste des messages pour tous les utilisateurs de la maison\n"
    "        if SOCKETIO_AVAILABLE and socketio:\n"
    "            safe_socketio_emit('messages_list_update', {\n"
    "                'house_id': house_id,\n"
    "                'action': 'baby_tracking',\n"
    "                'sender_email': session['user'],\n"
    "                'sender_name': user_name,\n"
    "                'task_type': task_type\n"
    "            }, room=f'house_{house_id}', namespace='/', broadcast=True)\n"
    "            _dbg(f\"\ud83d\udd0c WebSocket: Synchronisation messagerie baby_tracking pour house_{house_id}\")\n"
    "    except Exception as e:\n"
    "        _dbg(f\"\u274c Erreur cr\u00e9ation message baby_tracking: {e}\")\n"
    "        import traceback\n"
    "        traceback.print_exc()\n"
)

NEW_BABY = (
    "    # \ud83d\udd14 Cr\u00e9er le message syst\u00e8me + envoyer push et WebSocket \u00e0 tous (sauf auteur)\n"
    "    # create_system_message : INSERT + socketio 'system_message' + notify_house_members (push)\n"
    "    try:\n"
    "        create_system_message(\n"
    "            house_id,\n"
    "            message_text,\n"
    "            message_type='baby_tracking',\n"
    "            sender_email=session['user'],\n"
    "            send_push=True\n"
    "        )\n"
    "        # Marquer comme lu pour l'auteur : il ne doit pas voir sa propre pastille\n"
    "        try:\n"
    "            _conn2 = get_db_connection()\n"
    "            _row2 = _conn2.execute(\n"
    "                \"SELECT id FROM messages WHERE house_id=? AND sender_email=? \"\n"
    "                \"AND message_type='baby_tracking' ORDER BY id DESC LIMIT 1\",\n"
    "                (house_id, session['user'])\n"
    "            ).fetchone()\n"
    "            _conn2.close()\n"
    "            if _row2:\n"
    "                mark_message_as_read(_row2[0], session['user'])\n"
    "        except Exception as _e2:\n"
    "            _dbg(f\"\u26a0\ufe0f Marquage lu auteur baby \u00e9chou\u00e9: {_e2}\")\n"
    "    except Exception as e:\n"
    "        _dbg(f\"\u274c Erreur create_system_message baby_tracking: {e}\")\n"
    "        import traceback\n"
    "        traceback.print_exc()\n"
)

if OLD_BABY in app:
    app = app.replace(OLD_BABY, NEW_BABY, 1)
    print("\u2705 Fix 1 app.py : save_baby_tracking -> create_system_message")
else:
    print("\u274c Fix 1 app.py : texte non trouv\u00e9 (d\u00e9j\u00e0 appliqu\u00e9 ?)")
    sys.exit(1)

with open(path_app, 'w', encoding='utf-8') as f:
    f.write(app)

# ══════════════════════════════════════════════════════════════════
# FIX 2 — menu.html : handlers socket.on reminder_added / reminder_toggle
# ══════════════════════════════════════════════════════════════════
path_menu = 'templates/menu.html'
with open(path_menu, encoding='utf-8') as f:
    menu = f.read()

# Point d'insertion : après le handler all_messages_read
OLD_ANCHOR = (
    "                        socket.on('all_messages_read', function(data) {\n"
    "                            console.log('WebSocket: Messages marqu\u00e9s comme lus', data);\n"
    "                            if (data.reader_email === userEmail) {\n"
    "                                refreshAllBadges();\n"
    "                            }\n"
    "                        });"
)

NEW_ANCHOR = (
    "                        socket.on('all_messages_read', function(data) {\n"
    "                            console.log('WebSocket: Messages marqu\u00e9s comme lus', data);\n"
    "                            if (data.reader_email === userEmail) {\n"
    "                                refreshAllBadges();\n"
    "                            }\n"
    "                        });\n"
    "\n"
    "                        // \ud83d\uded2 Article ajout\u00e9 \u00e0 la liste de courses\n"
    "                        // Met \u00e0 jour le badge courses pour TOUS les joueurs en temps r\u00e9el\n"
    "                        socket.on('reminder_added', function(data) {\n"
    "                            var badge = document.getElementById('courses-nav-badge');\n"
    "                            if (badge) {\n"
    "                                var n = data.pending_count || 0;\n"
    "                                if (n > 0) {\n"
    "                                    badge.textContent = n < 100 ? n : '99+';\n"
    "                                    badge.style.display = '';\n"
    "                                } else {\n"
    "                                    badge.style.display = 'none';\n"
    "                                }\n"
    "                            }\n"
    "                        });\n"
    "\n"
    "                        // \ud83d\uded2 Article coch\u00e9/d\u00e9coch\u00e9 dans la liste de courses\n"
    "                        // Met \u00e0 jour le badge courses pour TOUS les joueurs en temps r\u00e9el\n"
    "                        socket.on('reminder_toggle', function(data) {\n"
    "                            var badge = document.getElementById('courses-nav-badge');\n"
    "                            if (badge) {\n"
    "                                var n = (data.pending_count !== undefined) ? data.pending_count : 0;\n"
    "                                if (n > 0) {\n"
    "                                    badge.textContent = n < 100 ? n : '99+';\n"
    "                                    badge.style.display = '';\n"
    "                                } else {\n"
    "                                    badge.style.display = 'none';\n"
    "                                }\n"
    "                            }\n"
    "                        });"
)

if OLD_ANCHOR in menu:
    menu = menu.replace(OLD_ANCHOR, NEW_ANCHOR, 1)
    print("\u2705 Fix 2 menu.html : handlers reminder_added + reminder_toggle ajout\u00e9s")
else:
    print("\u274c Fix 2 menu.html : ancre all_messages_read non trouv\u00e9e")
    sys.exit(1)

with open(path_menu, 'w', encoding='utf-8') as f:
    f.write(menu)

print("\u2705 Toutes les corrections appliqu\u00e9es")
