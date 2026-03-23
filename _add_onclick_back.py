#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trouver le bouton beta-dot et lui ajouter onclick
for i in range(len(lines)):
    if 'class="beta-dot"' in lines[i] and 'id="burgerBtn"' in lines[i]:
        print(f"✅ Trouvé le bouton beta-dot ligne {i+1}")
        
        # Vérifier s'il n'a pas déjà onclick
        if 'onclick=' not in lines[i]:
            # Ajouter onclick juste avant role="button"
            lines[i] = lines[i].replace(
                'role="button"',
                'onclick="openBurgerMenu()" role="button"'
            )
            print("✅ Ajouté onclick='openBurgerMenu()' au bouton")
        else:
            print("⚠️  onclick déjà présent")
        break

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("🎯 Le bouton appellera openBurgerMenu() au clic")
