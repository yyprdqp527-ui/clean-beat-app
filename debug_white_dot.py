#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script pour identifier le point blanc mystérieux"""

import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("=== Recherche d'éléments suspects ===\n")

# 1. Chercher les éléments avec animation et position fixed/absolute
print("1. Éléments avec animation:")
animations = re.findall(r'animation:\s*[^;]+;', content)
unique_anims = sorted(set(animations))
for anim in unique_anims:
    if 'pulse' in anim.lower() or 'blink' in anim.lower():
        print(f"   - {anim}")

print("\n2. Éléments circulaires (border-radius: 50%):")
# Chercher les sections avec border-radius: 50% et leur contexte
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'border-radius:50%' in line.replace(' ', '') or 'border-radius: 50%' in line:
        # Afficher quelques lignes de contexte
        if 'white' in line.lower() or '#fff' in line.lower() or '255,255,255' in line.replace(' ', ''):
            print(f"   Ligne {i+1}: {line.strip()[:100]}")

print("\n3. Éléments avec z-index élevé et position fixed:")
for i, line in enumerate(lines):
    if 'position:fixed' in line.replace(' ', '') or 'position: fixed' in line:
        if 'z-index' in line:
            print(f"   Ligne {i+1}: {line.strip()[:120]}")

print("\n4. Recherche de 'beta' dans le HTML:")
for i, line in enumerate(lines):
    if 'beta' in line.lower() and ('style=' in line or 'class=' in line):
        if i >= 3920 and i <= 3935:  # Zone où était le beta-dot
            print(f"   Ligne {i+1}: {line.strip()}")
