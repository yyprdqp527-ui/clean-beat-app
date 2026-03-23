#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Chercher les patterns suspects
suspects = []

for i, line in enumerate(lines, 1):
    stripped = line.strip()
    
    # Pattern 1: } catch sans { ou try visible sur la même ligne ou ligne précédente
    if re.search(r'^\s*}\s*catch\s*[\({]', line):
        if i > 1:
            prev = lines[i-2].strip()
            if not ('try' in prev or '{' in prev):
                suspects.append((i, "} catch sans try visible", line.strip()))
    
    # Pattern 2: Ligne qui commence par return avec très peu d'indentation
    if re.match(r'^return\s', stripped):
        suspects.append((i, "return sans indentation", stripped))
    
    # Pattern 3: } suivi directement d'un mot-clé sans espace/parenthèse
    if re.search(r'}\s*[a-z]', stripped) and 'catch' not in stripped and 'finally' not in stripped and 'else' not in stripped:
        suspects.append((i, "} collé à un mot", stripped[:80]))

    # Pattern 4: catch ou try sans accolades
    if re.search(r'(try|catch)\s+[^{]', stripped) and stripped.endswith((';', ')')):
        suspects.append((i, "try/catch sans accolade", stripped[:80]))

if suspects:
    print(f"🔍 Trouvé {len(suspects)} patterns suspects:\n")
    for line_num, reason, content in suspects:
        print(f"Ligne {line_num}: {reason}")
        print(f"   {content}")
        print()
else:
    print("✅ Aucun pattern suspect évident trouvé")
