#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Réduire le bouton burger et ajouter espacement
"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Réduire taille du bouton burger
content = content.replace('width: 46px;', 'width: 38px;')
content = content.replace('height: 46px;', 'height: 38px;')
content = content.replace('border-radius: 12px;', 'border-radius: 10px;', 1)  # Seulement le premier (beta-dot)

# 2. Réduire taille du hamburger icon
content = content.replace("font-size: 22px;", "font-size: 18px;", 1)  # Dans .beta-dot::before

# 3. Ajouter espacement à header-left-actions
content = content.replace(
    ".header-left-actions {\n    position: absolute; left: 10px;",
    ".header-left-actions {\n    position: absolute; left: 10px; margin-right: 8px;"
)

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Bouton burger réduit: 46px → 38px")
print("✅ Icon hamburger réduit: 22px → 18px")
print("✅ Espacement ajouté: margin-right: 8px")
