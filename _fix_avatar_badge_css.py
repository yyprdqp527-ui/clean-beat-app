#!/usr/bin/env python3
"""
Ajouter display: none !important au CSS .avatar-notification-badge
"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Trouver le bloc CSS et remplacer display: flex par display: none !important
old_css = '''        /* Badge de notification sur l'avatar */
        .avatar-notification-badge {
            position: absolute;
            top: -4px;
            right: -4px;
            background: linear-gradient(135deg, #FF4444 0%, #FF6B6B 100%);
            color: white;
            font-size: 10px;
            font-weight: 800;
            min-width: 22px;
            height: 22px;
            border-radius: 11px;
            display: flex;
            align-items: center;
            justify-content: center;'''

new_css = '''        /* Badge de notification sur l'avatar */
        .avatar-notification-badge {
            position: absolute;
            top: -4px;
            right: -4px;
            background: linear-gradient(135deg, #FF4444 0%, #FF6B6B 100%);
            color: white;
            font-size: 10px;
            font-weight: 800;
            min-width: 22px;
            height: 22px;
            border-radius: 11px;
            display: none !important; /* 🚫 Badges avatars DÉSACTIVÉS - notifications dans le menu fixe uniquement */
            align-items: center;
            justify-content: center;'''

if old_css in content:
    content = content.replace(old_css, new_css)
    with open('templates/menu.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ CSS modifié - display: none !important ajouté")
else:
    print("❌ Bloc CSS non trouvé - peut-être déjà modifié ?")
    if 'display: none' in content and 'avatar-notification-badge' in content:
        print("   (Le CSS semble déjà contenir display: none)")
    else:
        print("   Recherche du pattern actuel...")
        # Trouver avatar-notification-badge dans le fichier
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '.avatar-notification-badge {' in line:
                print(f"   Trouvé ligne {i+1}: {line}")
                for j in range(20):
                    if i+j < len(lines):
                        print(f"      {i+j+1}: {lines[i+j]}")
                break
