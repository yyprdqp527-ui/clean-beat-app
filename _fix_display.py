import re

# ═══════════════════════════════════════════════════════════
# 1. menu.html — CSS pastille rose + HTML sur chambre_bebe
# ═══════════════════════════════════════════════════════════
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    menu = f.read()

# 1a. Ajouter CSS .room-baby-dot juste après .room-mission-dot
old_css = 'pointer-events: none;\n            z-index: 10;\n        }\n\n        /* Responsive isométrique */'
new_css = '''pointer-events: none;
            z-index: 10;
        }

        /* Pastille rose chambre bébé */
        .room-baby-dot {
            position: absolute;
            top: -8px;
            left: -8px;
            min-width: 26px;
            height: 26px;
            padding: 0 7px;
            border-radius: 13px;
            background: #F472B6;
            color: #fff;
            font-size: 13px;
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
            box-shadow: 0 2px 8px rgba(244,114,182,0.7);
            animation: pulse-badge 2s ease-in-out infinite;
            pointer-events: none;
            z-index: 10;
        }

        /* Responsive isométrique */'''

if old_css in menu:
    menu = menu.replace(old_css, new_css)
    print('CSS pastille rose OK')
else:
    print('CSS NOT FOUND')

# 1b. Ajouter le span .room-baby-dot dans la boucle des room cards
# Juste après le span room-mission-dot
old_html = '''                                        <span class="room-mission-dot"
                                              title="Mission(s) en attente"
                                              {% if room.category not in rooms_with_new_missions %}style="display:none"{% endif %}>
                                            {{ rooms_with_new_missions[room.category] if room.category in rooms_with_new_missions else '' }}
                                        </span>
                                    </div>
                                </a>
                                {% endfor %}'''
new_html = '''                                        <span class="room-mission-dot"
                                              title="Mission(s) en attente"
                                              {% if room.category not in rooms_with_new_missions %}style="display:none"{% endif %}>
                                            {{ rooms_with_new_missions[room.category] if room.category in rooms_with_new_missions else '' }}
                                        </span>
                                        {% if room.category == 'chambre_bebe' and unread_baby_tracking|default(0) > 0 %}
                                        <span class="room-baby-dot" title="Nouveau suivi bébé">👶</span>
                                        {% endif %}
                                    </div>
                                </a>
                                {% endfor %}'''

if old_html in menu:
    menu = menu.replace(old_html, new_html)
    print('HTML pastille rose OK')
else:
    print('HTML NOT FOUND — trying to locate...')
    idx = menu.find('room-mission-dot')
    print(repr(menu[idx:idx+500]))

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(menu)
print('menu.html saved.')


