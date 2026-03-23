#!/usr/bin/env python3
"""
Correction précise : restructurer la carte joueur html
pour mettre le prénom sous l'avatar et réorganiser les badges
"""

with open('templates/gameplay.html', 'r', encoding='utf-8') as f:
    c = f.read()

# On utilise les numéros de ligne pour repérer exactement la zone à remplacer
lines = c.split('\n')

# Trouver la ligne avec gw-rank dans la section HTML (pas CSS)
# On cherche "            <div class=\"gw-rank\">{{ medal }}</div>"
target_start = None
target_end = None

for i, line in enumerate(lines):
    if '<div class="gw-rank">{{ medal }}</div>' in line:
        target_start = i
    if target_start and '<div class="gw-tasks-list"></div>' in line:
        target_end = i
        break

if target_start is None or target_end is None:
    print(f"❌ Zone non trouvée: start={target_start}, end={target_end}")
    exit(1)

print(f"✅ Zone trouvée: lignes {target_start+1} → {target_end+1}")
print("Lignes actuelles:")
for i in range(target_start, target_end+1):
    print(f"  {i+1}: {lines[i]}")

# Remplacement par le nouveau code
new_lines = [
    '            <div class="gw-avatar-col">',
    '                <div class="gw-rank">{{ medal }}</div>',
    '                {% if p.avatar_file %}<img class="gw-avatar-img" src="{{ url_for(\'static\', filename=\'avatars/\'+p.avatar_file) }}" alt="{{ p.name|e }}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div class="gw-avatar-emoji" style="display:none;">👤</div>',
    '                {% elif p.avatar_url %}<img class="gw-avatar-img" src="{{ p.avatar_url }}" alt="{{ p.name|e }}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';"><div class="gw-avatar-emoji" style="display:none;">👤</div>',
    '                {% elif p.avatar %}<div class="gw-avatar-emoji">{{ p.avatar }}</div>',
    '                {% else %}<div class="gw-avatar-emoji">👤</div>{% endif %}',
    '                <div class="gw-avatar-label">{{ p.name|e }}</div>',
    '            </div>',
    '            <div class="gw-info">',
    '                <div class="gw-pts-row">',
    '                    <div class="gw-name">{{ p.name|e }}</div>',
    '                    <div class="gw-pts">{{ p.daily_points|default(0) }} pts</div>',
    '                    {% if p.skull_active|default(false) %}<span class="gw-skull">💀</span>{% elif p.skull_pending|default(false) %}<span class="gw-skull" style="color:#FDAE54;">💀?</span>{% elif p.skull_count|default(0)>0 %}<span class="gw-skull">💀×{{ p.skull_count }}</span>{% endif %}',
    '                </div>',
    '                <div class="gw-bar-wrap"><div class="gw-bar-fill" data-pct="{{ bar_pct }}" data-color="{{ p.player_color_hex if p.player_color_hex else \'\' }}" style="width:0%;"></div></div>',
    '            </div>',
    '            <div class="gw-tasks-list"></div>',
]

# Supprimer les anciennes lignes et insérer les nouvelles
lines = lines[:target_start] + new_lines + lines[target_end+1:]

c = '\n'.join(lines)

with open('templates/gameplay.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("\n✅ HTML cartes joueurs restructuré (prénom sous avatar)")
