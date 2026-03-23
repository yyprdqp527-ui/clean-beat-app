#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remplace les caractères problématiques dans les console.log du script burger
"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacer les apostrophes et caractères accentués dans les console.log
replacements = [
    ("console.log('openBurgerMenu appelée!');", 
     "console.log('openBurgerMenu appelee');"),
    
    ("console.log('closeBurgerMenu appelée!');", 
     "console.log('closeBurgerMenu appelee');"),
    
    ("console.log('Fonctions burger définies');", 
     "console.log('Fonctions burger definies');"),
    
    ("console.log('Event listener ajouté au bouton close');", 
     "console.log('Event listener ajoute au bouton close');"),
    
    ("console.log('Event listener ajouté à l'overlay');", 
     "console.log('Event listener ajoute a overlay');"),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Caractères accentués et apostrophes supprimés des console.log")
print("🔄 Redémarrez Flask")
