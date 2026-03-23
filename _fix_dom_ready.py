#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trouver l'IIFE qui configure le burger menu
for i in range(len(lines)):
    if '(function() {' in lines[i] and i > 4900 and i < 4920:
        # Trouver la ligne avec const burgerBtn juste après
        if 'const burgerBtn = document.getElementById' in lines[i+1]:
            print(f"✅ Trouvé l'IIFE ligne {i+1}")
            
            # Remplacer (function() { par document.addEventListener('DOMContentLoaded', function() {
            lines[i] = lines[i].replace(
                '(function() {',
                "document.addEventListener('DOMContentLoaded', function() {"
            )
            
            # Trouver la fermeture })(); et la remplacer par });
            for j in range(i, min(i+50, len(lines))):
                if '})();' in lines[j] and 'burgerBtn' not in lines[j]:
                    print(f"✅ Trouvé la fermeture ligne {j+1}")
                    # Compter les occurrences pour ne remplacer que la bonne
                    if lines[j].strip() == '})();':
                        lines[j] = lines[j].replace('})();', '});')
                        print(f"✅ Remplacé la fermeture IIFE par addEventListener ligne {j+1}")
                        break
            break

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("🎯 Le burger menu s'initialisera maintenant après le chargement du DOM")
