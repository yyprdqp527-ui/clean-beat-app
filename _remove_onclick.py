#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Supprimer onclick="openBurgerMenu()" du beta-dot
content = content.replace(
    'onclick="openBurgerMenu()"',
    ''
)

# Remplacer "Bêta testeur" par "Menu burger" dans le title
content = content.replace(
    'title="Bêta testeur"',
    'title="Menu burger"'
)

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ onclick supprimé du bouton beta-dot")
print("✅ Title changé en 'Menu burger'")
print("🎯 Le bouton utilisera maintenant addEventListener (ligne 4917)")
