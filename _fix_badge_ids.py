#!/usr/bin/env python3
"""Fix: renommer les IDs HTML pour correspondre aux IDs attendus par le JS."""
content = open('templates/menu.html', encoding='utf-8').read()

# 1. Supprimer CSS display:none sur les badges CW
old1 = '/* Badges du header CW masqués — remplacés par la barre nav fixe du bas */\n    #messages-nav-badge, #courses-nav-badge { display: none !important; }\n    .cw-tab-badge {'
new1 = '.cw-tab-badge {'
assert old1 in content, 'PATTERN 1 NOT FOUND'

# 2. Renommer id messages-nav-badge → bottomNavMessagesBadge
old2 = 'id="messages-nav-badge"'
new2 = 'id="bottomNavMessagesBadge"'
assert old2 in content, 'PATTERN 2 NOT FOUND'

# 3. Renommer id courses-nav-badge → bottomNavCoursesBadge
old3 = 'id="courses-nav-badge"'
new3 = 'id="bottomNavCoursesBadge"'
assert old3 in content, 'PATTERN 3 NOT FOUND'

content = content.replace(old1, new1, 1)
content = content.replace(old2, new2, 1)
content = content.replace(old3, new3, 1)

open('templates/menu.html', 'w', encoding='utf-8').write(content)
print('✅ 3 modifications appliquées')

# Vérification
c2 = open('templates/menu.html', encoding='utf-8').read()
print('bottomNavMessagesBadge présent:', 'id="bottomNavMessagesBadge"' in c2)
print('bottomNavCoursesBadge présent:', 'id="bottomNavCoursesBadge"' in c2)
print('display none supprimé:', '#messages-nav-badge, #courses-nav-badge { display: none' not in c2)
