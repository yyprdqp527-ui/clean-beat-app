#!/usr/bin/env python3
"""Vérifier que les modifications sont présentes dans menu.html"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check for the function
if 'bottomNavMessagesBadge' in content:
    print('✅ bottomNavMessagesBadge trouvé dans menu.html')
    print(f'   Occurrences: {content.count("bottomNavMessagesBadge")}')
else:
    print('❌ bottomNavMessagesBadge NON trouvé')

if 'display: none' in content and 'Badges avatars DÉSACTIVÉS' in content:
    print('✅ CSS .avatar-notification-badge display:none trouvé')
else:
    print('❌ CSS .avatar-notification-badge display:none NON trouvé')

# Vérifier comments.html
with open('templates/comments.html', 'r', encoding='utf-8') as f:
    comments_content = f.read()

if 'typeof window.cbToast' in comments_content:
    print('✅ cbToast fix trouvé dans comments.html')
else:
    print('❌ cbToast fix NON trouvé dans comments.html')
