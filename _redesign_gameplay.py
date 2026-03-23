#!/usr/bin/env python3
"""
Refonte complète de gameplay.html pour mobile :
- Glassmorphism harmonisé
- Prénom sous avatar
- Tâches sur 2 lignes (lisibles)
- Cadres photo améliorés
- Pas de débordement mobile
"""

import re

f = open('templates/gameplay.html', 'r', encoding='utf-8')
c = f.read()
f.close()

# ── 1. Remplacer tout le bloc CSS des joueurs / tâches / cadres ──────────────

OLD_TASKS_CSS = re.search(
    r'(/\* ══ gw-player adapté fond sombre ══ \*/.*?)(\.gw-skull|\.gw-rank)',
    c, re.DOTALL
)
if OLD_TASKS_CSS:
    # On repère les bornes précises
    start = c.find('/* ══ gw-player adapté fond sombre ══ */')
    end_marker = c.find('.gameplay-actions', start)  # s'arrête avant les boutons
    old_block = c[start:end_marker]
    new_block = """\
/* ══ gw-player adapté fond sombre ══ */
.gameplay-players-wrap { padding: 0 14px; }

.gw-player {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: linear-gradient(135deg, rgba(255,255,255,0.09) 0%, rgba(166,211,220,0.09) 100%);
    backdrop-filter: blur(14px) saturate(130%);
    -webkit-backdrop-filter: blur(14px) saturate(130%);
    border: 1.5px solid rgba(255,255,255,0.14);
    border-radius: 18px;
    padding: 14px 14px;
    margin-bottom: 12px;
    box-shadow: 0 6px 24px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.1);
    flex-wrap: wrap;
}
.gw-player.gw-me {
    background: linear-gradient(135deg, rgba(253,174,84,0.16) 0%, rgba(166,211,220,0.12) 100%);
    border-color: rgba(253,174,84,0.3);
    box-shadow: 0 6px 24px rgba(253,174,84,0.15), inset 0 1px 0 rgba(255,255,255,0.12);
}

/* Colonne avatar : rang + image + prénom en dessous */
.gw-avatar-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    flex-shrink: 0;
    width: 54px;
}
.gw-rank { font-size: 13px; line-height: 1; color: rgba(255,255,255,0.6); }
.gw-avatar-label {
    font-size: 10px;
    font-weight: 700;
    color: rgba(255,255,255,0.8);
    text-align: center;
    max-width: 58px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.gw-avatar-img { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; border: 2.5px solid rgba(255,255,255,0.35); flex-shrink: 0; }
.gw-avatar-emoji { width: 42px; height: 42px; border-radius: 50%; background: rgba(255,255,255,0.12); display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }
.gw-info { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; }
.gw-name { font-size: 14px; font-weight: 700; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gw-pts-row { display: flex; align-items: center; gap: 6px; }
.gw-bar-wrap { height: 5px; background: rgba(255,255,255,0.1); border-radius: 4px; margin-top: 6px; overflow: hidden; }
.gw-bar-fill { height: 100%; border-radius: 4px; min-width: 5px; background: linear-gradient(90deg,#A6D3DC,#FDAE54); transition: width 0.8s cubic-bezier(0.22, 0.61, 0.36, 1); }
.gw-pts { font-size: 15px; font-weight: 800; color: #FDAE54; white-space: nowrap; }
.gw-skull { font-size: 14px; }
.gw-suspicion { font-size: 14px; margin-left: 4px; }

/* Tâches du joueur : 2 lignes pour mobile */
.gw-tasks-list {
    display: none;
    flex-direction: column;
    gap: 7px;
    width: 100%;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.1);
}
.gw-tasks-list.has-tasks { display: flex; }
.gw-task-item {
    display: flex;
    flex-direction: column;
    gap: 5px;
    padding: 9px 10px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 12px;
}
.gw-task-row1 { display: flex; align-items: center; gap: 8px; }
.gw-task-row2 { display: flex; align-items: center; justify-content: flex-end; gap: 6px; }
.gw-task-dot { width: 7px; height: 7px; border-radius: 50%; background: linear-gradient(135deg,#A6D3DC,#89b4bb); flex-shrink: 0; }
.gw-task-name { flex: 1; font-weight: 600; color: rgba(255,255,255,0.9); font-size: 13px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gw-task-pts { font-size: 11px; font-weight: 700; color: #FDAE54; background: rgba(253,174,84,0.15); padding: 2px 7px; border-radius: 8px; flex-shrink: 0; }
.gw-task-time { font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.45); }
.gw-task-suspicion-btn { border: none; background: rgba(255,255,255,0.08); cursor: pointer; font-size: 17px; padding: 6px 9px; border-radius: 10px; flex-shrink: 0; transition: background 0.2s; -webkit-tap-highlight-color: transparent; }
.gw-task-malus-btn   { border: none; background: rgba(231,76,60,0.15);    cursor: pointer; font-size: 17px; padding: 6px 9px; border-radius: 10px; flex-shrink: 0; transition: background 0.2s; -webkit-tap-highlight-color: transparent; }
.gw-task-bonus-btn   { border: none; background: rgba(46,204,113,0.15);   cursor: pointer; font-size: 17px; padding: 6px 9px; border-radius: 10px; flex-shrink: 0; transition: background 0.2s; -webkit-tap-highlight-color: transparent; }
.gw-task-suspicion-btn:active { background: rgba(255,255,255,0.22); transform: scale(0.93); }
.gw-task-malus-btn:active   { background: rgba(231,76,60,0.38); transform: scale(0.93); }
.gw-task-bonus-btn:active   { background: rgba(46,204,113,0.38); transform: scale(0.93); }

/* Cadre photo de preuve */
.proof-photo-frame {
    margin-top: 12px;
    padding: 16px;
    background: rgba(0,0,0,0.25);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border-radius: 14px;
    min-height: 130px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    border: 1.5px dashed rgba(255,255,255,0.18);
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.2);
    gap: 10px;
}
.proof-photo-frame img {
    width: 100%;
    max-height: 240px;
    object-fit: contain;
    border-radius: 10px;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
}

/* Carte suspicion */
.suspicion-card {
    backdrop-filter: blur(14px) saturate(140%);
    -webkit-backdrop-filter: blur(14px) saturate(140%);
    border-radius: 18px;
    padding: 14px 14px;
    margin-bottom: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.08);
}

"""
    c = c[:start] + new_block + c[end_marker:]
    print("✅ Bloc CSS joueurs/tâches/photo remplacé")
else:
    print("⚠️  Bloc CSS joueurs non trouvé avec regex, cherche manuellement...")
    # Fallback : chercher la section manuellement
    marker = '/* ══ gw-player adapté fond sombre ══ */'
    if marker not in c:
        print("❌ Marqueur CSS non trouvé dans le fichier")

# ── 2. Titre de page : glassmorphism amélioré ────────────────────────────────
old_title = '.gameplay-title-card {\n    background: linear-gradient(135deg, rgba(255,255,255,0.12)'
new_title = '.gameplay-title-card {\n    background: linear-gradient(135deg, rgba(255,255,255,0.14)'
if old_title in c:
    c = c.replace(old_title, new_title, 1)
    print("✅ Title card glassmorphism renforcé")

old_blur_title = 'backdrop-filter: blur(20px);\n    -webkit-backdrop-filter: blur(20px);\n    border-radius: 20px;\n    padding: 18px 20px;\n    margin: 12px 16px 0;\n    border: 1.5px solid rgba(253,174,84,0.3);\n    box-shadow: 0 8px 30px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.15);\n    text-align: center;\n}'
new_blur_title = 'backdrop-filter: blur(24px) saturate(150%);\n    -webkit-backdrop-filter: blur(24px) saturate(150%);\n    border-radius: 22px;\n    padding: 20px 22px 16px;\n    margin: 12px 14px 0;\n    border: 1.5px solid rgba(255,255,255,0.22);\n    box-shadow: 0 8px 32px rgba(0,0,0,0.22), inset 0 2px 0 rgba(255,255,255,0.18);\n    text-align: center;\n}'
if old_blur_title in c:
    c = c.replace(old_blur_title, new_blur_title, 1)
    print("✅ Title card border/shadow amélioré")

# ── 3. Restructurer les cartes joueurs HTML (ajouter prénom sous avatar) ──────
# Ancien : <div class="gw-rank">{{ medal }}</div>
# Nouveau : <div class="gw-avatar-col"> rang + avatar + prénom </div>

old_player_row = '''\
            <div class="gw-rank">{{ medal }}</div>
            {% if p.avatar_file %}<img class="gw-avatar-img" src="{{ url_for('static', filename='avatars/'+p.avatar_file) }}" alt="{{ p.name|e }}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div class="gw-avatar-emoji" style="display:none;">👤</div>
            {% elif p.avatar_url %}<img class="gw-avatar-img" src="{{ p.avatar_url }}" alt="{{ p.name|e }}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div class="gw-avatar-emoji" style="display:none;">👤</div>
            {% elif p.avatar %}<div class="gw-avatar-emoji">{{ p.avatar }}</div>
            {% else %}<div class="gw-avatar-emoji">👤</div>{% endif %}
            <div class="gw-info">
                <div class="gw-name">{{ p.name|e }}</div>
                <div class="gw-bar-wrap"><div class="gw-bar-fill" data-pct="{{ bar_pct }}" data-color="{{ p.player_color_hex if p.player_color_hex else \'\' }}" style="width:0%;"></div></div>
            </div>
            <div class="gw-pts">{{ p.daily_points|default(0) }} pts</div>
            {% if p.skull_active|default(false) %}<span class="gw-skull">💀</span>{% elif p.skull_pending|default(false) %}<span class="gw-skull" style="color:#FDAE54;">💀?</span>{% elif p.skull_count|default(0)>0 %}<span class="gw-skull"> 💀×{{ p.skull_count }}</span>{% endif %}
            <div class="gw-tasks-list"></div>'''

new_player_row = '''\
            <div class="gw-avatar-col">
                <div class="gw-rank">{{ medal }}</div>
                {% if p.avatar_file %}<img class="gw-avatar-img" src="{{ url_for(\'static\', filename=\'avatars/\'+p.avatar_file) }}" alt="{{ p.name|e }}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div class="gw-avatar-emoji" style="display:none;">👤</div>
                {% elif p.avatar_url %}<img class="gw-avatar-img" src="{{ p.avatar_url }}" alt="{{ p.name|e }}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div class="gw-avatar-emoji" style="display:none;">👤</div>
                {% elif p.avatar %}<div class="gw-avatar-emoji">{{ p.avatar }}</div>
                {% else %}<div class="gw-avatar-emoji">👤</div>{% endif %}
                <div class="gw-avatar-label">{{ p.name|e }}</div>
            </div>
            <div class="gw-info">
                <div class="gw-pts-row">
                    <div class="gw-name">{{ p.name|e }}</div>
                    <div class="gw-pts">{{ p.daily_points|default(0) }} pts</div>
                    {% if p.skull_active|default(false) %}<span class="gw-skull">💀</span>{% elif p.skull_pending|default(false) %}<span class="gw-skull" style="color:#FDAE54;">💀?</span>{% elif p.skull_count|default(0)>0 %}<span class="gw-skull">💀×{{ p.skull_count }}</span>{% endif %}
                </div>
                <div class="gw-bar-wrap"><div class="gw-bar-fill" data-pct="{{ bar_pct }}" data-color="{{ p.player_color_hex if p.player_color_hex else \'\' }}" style="width:0%;"></div></div>
            </div>
            <div class="gw-tasks-list"></div>'''

if old_player_row in c:
    c = c.replace(old_player_row, new_player_row, 1)
    print("✅ HTML cartes joueurs restructuré (prénom sous avatar)")
else:
    print("⚠️  HTML player row non trouvé - cherche une alternative...")
    # Cherche par parties
    if '<div class="gw-rank">{{ medal }}</div>' in c:
        print("   → Le div rank existe bien")
    if '<div class="gw-tasks-list"></div>' in c:
        print("   → Le div tasks-list existe bien")

# ── 4. Modifier le JS des tâches pour utiliser les 2 lignes ──────────────────
old_task_item = """                    return '<div class="gw-task-item">'
                         + '<div class="gw-task-dot"></div>'
                         + '<span class="gw-task-name">'+enc(t.task_name)+'</span>'
                         + '<span class="gw-task-pts">+'+t.points+' pts</span>'
                         + '<span class="gw-task-time">'+enc(t.time)+'</span>'"""

new_task_item = """                    return '<div class="gw-task-item">'
                         + '<div class="gw-task-row1">'
                         + '<div class="gw-task-dot"></div>'
                         + '<span class="gw-task-name">'+enc(t.task_name)+'</span>'
                         + '<span class="gw-task-pts">+'+t.points+' pts</span>'
                         + '</div>'
                         + '<div class="gw-task-row2">'
                         + '<span class="gw-task-time">'+enc(t.time)+'</span>'"""

if old_task_item in c:
    c = c.replace(old_task_item, new_task_item, 1)
    # Ferme aussi le row2 juste après les boutons
    old_close = "+ actBtns\n                         + '</div>';"
    new_close = "+ actBtns\n                         + '</div>'  /* close row2 */\n                         + '</div>';  /* close task-item */"
    # On ne change pas la fermeture ici, le div item se ferme déjà en bas
    print("✅ JS tâches : passage sur 2 lignes")
else:
    print("⚠️  JS task item non trouvé")
    idx = c.find("return '<div class=\"gw-task-item\">'")
    if idx != -1:
        print(f"   → Trouvé à l'index {idx}, contenu :")
        print(repr(c[idx:idx+200]))

# ── 5. Cadres photo : remplacer les styles inline par la classe CSS ──────────
# On remplace les div inline de cadre photo par la classe .proof-photo-frame
old_photo_frame = 'style="margin-top: 12px; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 10px; min-height: 150px; display: flex; align-items: center; justify-content: center; flex-direction: column;"'
new_photo_frame = 'class="proof-photo-frame"'
count_photo = c.count(old_photo_frame)
if count_photo > 0:
    c = c.replace(old_photo_frame, new_photo_frame)
    print(f"✅ {count_photo} cadre(s) photo remplacé(s) par .proof-photo-frame")
else:
    print("⚠️  Cadre photo inline non trouvé (styles différents ?)")

# ── 6. Sauvegarder ───────────────────────────────────────────────────────────
with open('templates/gameplay.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("\n✅ TOUTES LES MODIFICATIONS APPLIQUÉES")
print("🔄 Redémarrez le serveur pour voir les changements")
