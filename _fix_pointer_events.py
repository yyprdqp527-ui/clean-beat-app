#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trouver le ::before et ajouter pointer-events: none
modified = False
for i in range(len(lines)):
    if '.beta-dot::before {' in lines[i]:
        # Chercher la ligne avec transform
        for j in range(i, min(i+15, len(lines))):
            if 'transform: translate(-50%, -50%)' in lines[j] and 'font-weight: bold;' in lines[j]:
                # Ajouter pointer-events après font-weight
                lines[j] = lines[j].replace(
                    'font-weight: bold;',
                    'font-weight: bold; pointer-events: none;'
                )
                modified = True
                print(f"✅ Modifié ligne {j+1}: ajouté pointer-events: none")
                break
            elif 'font-weight: bold;' in lines[j]:
                lines[j] = lines[j].replace(
                    'font-weight: bold;',
                    'font-weight: bold; pointer-events: none;'
                )
                modified = True
                print(f"✅ Modifié ligne {j+1}: ajouté pointer-events: none")
                break
        break

if modified:
    with open('templates/menu.html', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("🎯 Le symbole hamburger ne bloquera plus les clics!")
else:
    print("⚠️  Impossible de trouver la ligne à modifier")
    print("Recherche manuelle...")
    with open('templates/menu.html', 'r', encoding='utf-8') as f:
        content = f.read()
    if '.beta-dot::before' in content:
        print("✅ .beta-dot::before trouvé dans le fichier")
        # Ajoutons directement après le dernier ;
        if 'font-weight: bold;' in content and '.beta-dot::before' in content:
            content = content.replace(
                'font-weight: bold;\n}',
                'font-weight: bold;\n    pointer-events: none;\n}',
                1
            )
            with open('templates/menu.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Ajouté pointer-events: none via remplacement global")
