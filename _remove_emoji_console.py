#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supprime les émojis des console.log dans le script burger pour éviter les erreurs de syntaxe
"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacer les émojis dans les console.log du script burger
replacements = [
    ("console.log('🍔 openBurgerMenu appelée!');", 
     "console.log('openBurgerMenu appelée!');"),
    
    ("console.log('🍔 closeBurgerMenu appelée!');", 
     "console.log('closeBurgerMenu appelée!');"),
    
    ("console.error('🔴 burgerOverlay not found!');", 
     "console.error('burgerOverlay not found!');"),
    
    ("console.log('✅ Fonctions burger définies');", 
     "console.log('Fonctions burger définies');"),
    
    ("console.log('✅ Event listener ajouté au bouton close');", 
     "console.log('Event listener ajouté au bouton close');"),
    
    ("console.log('✅ Event listener ajouté à l'overlay');", 
     "console.log('Event listener ajouté à l'overlay');"),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Émojis supprimés des console.log")
print("🔄 Redémarrez Flask et videz le cache Safari")
