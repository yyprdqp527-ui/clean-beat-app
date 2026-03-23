#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trouver la ligne "/* Bouton burger */"
burger_line = None
for i, line in enumerate(lines):
    if '/* Bouton burger */' in line:
        burger_line = i
        break

if burger_line:
    # Trouver la fin du bloc .burger-menu { ... }
    brace_count = 0
    start = burger_line + 1  # ligne avec .burger-menu {
    end = start
    
    for i in range(start, len(lines)):
        brace_count += lines[i].count('{')
        brace_count -= lines[i].count('}')
        if brace_count == 0 and '}' in lines[i]:
            end = i + 1
            break
    
    # CSS de remplacement ORANGE GIGANTESQUE
    new_css = """        /* 🔴🔴🔴 BOUTON BURGER DEBUG ORANGE 80px 🔴🔴🔴 */
        .burger-menu {
            width: 80px !important;
            height: 80px !important;
            background: orange !important;
            border: 8px solid red !important;
            border-radius: 50% !important;
            display: flex !important;
            flex-direction: column;
            justify-content: center !important;
            align-items: center !important;
            gap: 8px !important;
            cursor: pointer !important;
            position: fixed !important;
            top: 15px !important;
            left: 15px !important;
            z-index: 999999 !important;
            visibility: visible !important;
            opacity: 1 !important;
            box-shadow: 0 0 50px rgba(255, 0, 0, 1) !important;
            padding: 0 !important;
            pointer-events: auto !important;
            transition: none !important;
        }
"""
    
    # Remplacer les lignes
    lines[burger_line:end] = [new_css]
    
    # Écrire le fichier
    with open('templates/menu.html', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✅ CSS burger-menu remplacé! (lignes {burger_line}-{end})")
    print("🔴 BOUTON ORANGE 80px avec bordure rouge 8px appliqué!")
else:
    print("❌ Bouton burger non trouvé")
