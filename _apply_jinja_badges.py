#!/usr/bin/env python3
"""
Fix: pré-affichage badges Jinja2 sans fetch réseau
Injecte les valeurs serveur (déjà calculées) en JS pour un affichage
immédiat, sans attendre le résultat du fetch /api/unread_counts.
"""

path = 'templates/menu.html'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Chercher la ligne "Appel IMMÉDIAT" (É = U+00C9, suivi de DIAT)
# en cherchant le bloc : commentaire + refreshAllBadges() + refreshMissionDots()
target_line = None
for i, l in enumerate(lines):
    if (('Appel' in l and 'DIAT' in l) or ('badges corrig' in l and 'ex' in l and 'cution' in l)):
        # Vérifier que les 2 lignes suivantes sont bien les appels attendus
        if i + 2 < len(lines) and 'refreshAllBadges' in lines[i+1] and 'refreshMissionDots' in lines[i+2]:
            target_line = i
            print(f"Trouvé ligne {i+1}: {repr(l.rstrip())}")
            break

if target_line is None:
    print("❌ Bloc 'Appel IMMÉDIAT' introuvable — recherche fallback sur le commentaire seul")
    for i, l in enumerate(lines):
        if 'badges corrig' in l and i > 6000:
            print(f"  Candidate ligne {i+1}: {repr(l.rstrip())}")
    exit(1)

# Vérifier les 2 lignes suivantes
l1 = lines[target_line+1].strip()
l2 = lines[target_line+2].strip()
print(f"Ligne +1: {repr(l1)}")
print(f"Ligne +2: {repr(l2)}")

if 'refreshAllBadges' not in l1 or 'refreshMissionDots' not in l2:
    print("❌ Structure inattendue, abandon")
    exit(1)

# Indentation (récupérée depuis la ligne target)
indent = lines[target_line].rstrip('\n')
indent = indent[:len(indent) - len(indent.lstrip())]

NEW_LINES = [
    f'{indent}// \u2705 Pr\u00e9-affichage INSTANT\u00c1N\u00c9 depuis les valeurs serveur (Jinja2, sans fetch ni r\u00e9seau)\n',
    f'{indent}// Garantit l\u2019affichage des badges d\u00e8s le premier pixel, m\u00eame si le r\u00e9seau\n',
    f'{indent}// iOS n\u2019est pas encore disponible (ouverture PWA apr\u00e8s push, r\u00e9veil background)\n',
    f'{indent}(function() {{\n',
    f'{indent}    try {{\n',
    f'{indent}        var _sc = {{\n',
    f'{indent}            unread_received: {{{{ unread_messages_count | default(0) | int }}}},\n',
    f'{indent}            unread_baby: {{{{ unread_baby_tracking | default(0) | int }}}},\n',
    f'{indent}            courses_pending_count: {{{{ courses_pending_count | default(0) | int }}}},\n',
    f'{indent}            pending_missions_count: {{{{ rooms_with_new_missions.values() | list | sum | default(0) | int }}}}\n',
    f'{indent}        }};\n',
    f'{indent}        var _sm = {{{{ rooms_with_new_missions | tojson }}}};\n',
    f'{indent}        updateUnreadBadge(_sc.unread_received);\n',
    f'{indent}        updateCoursesNavBadge(_sc.courses_pending_count);\n',
    f'{indent}        if (_sc.unread_baby > 0) {{\n',
    f'{indent}            var _bbc = document.querySelector(\'a.room-card[data-room="chambre_bebe"]\');\n',
    f'{indent}            if (_bbc) {{\n',
    f'{indent}                var _bbd = _bbc.querySelector(\'.room-baby-badge\');\n',
    f'{indent}                if (!_bbd) {{ _bbd = document.createElement(\'span\'); _bbd.className = \'room-baby-badge\'; _bbc.appendChild(_bbd); }}\n',
    f'{indent}                _bbd.textContent = _sc.unread_baby > 99 ? \'99+\' : _sc.unread_baby;\n',
    f'{indent}                _bbd.style.display = \'flex\';\n',
    f'{indent}            }}\n',
    f'{indent}        }}\n',
    f'{indent}        document.querySelectorAll(\'a.room-card[data-category]\').forEach(function(card) {{\n',
    f'{indent}            var count = _sm[card.getAttribute(\'data-category\')] || 0;\n',
    f'{indent}            if (count > 0) {{\n',
    f'{indent}                var dot = card.querySelector(\'.room-new-mission-badge\');\n',
    f'{indent}                if (!dot) {{ dot = document.createElement(\'span\'); dot.className = \'room-new-mission-badge\'; card.appendChild(dot); }}\n',
    f'{indent}                dot.textContent = count > 99 ? \'99+\' : count;\n',
    f'{indent}                dot.style.display = \'flex\';\n',
    f'{indent}            }}\n',
    f'{indent}        }});\n',
    f'{indent}        var _total = (_sc.unread_received > 0 ? 1 : 0)\n',
    f'{indent}                   + (_sc.unread_baby > 0 ? 1 : 0)\n',
    f'{indent}                   + (_sc.courses_pending_count > 0 ? 1 : 0)\n',
    f'{indent}                   + (_sc.pending_missions_count > 0 ? 1 : 0);\n',
    f'{indent}        if (typeof updateAppBadge === \'function\') updateAppBadge(_total);\n',
    f'{indent}    }} catch(e) {{}}\n',
    f'{indent}}})();\n',
    f'\n',
]

# Insérer avant la ligne target
lines = lines[:target_line] + NEW_LINES + lines[target_line:]

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'✅ Correctif appliqué — {len(NEW_LINES)} lignes insérées avant ligne {target_line+1}')
print(f'Nouveau nombre de lignes: {len(lines)}')
