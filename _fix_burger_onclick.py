#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Ajouter onclick au bouton beta-dot
content = content.replace(
    '<div class="beta-dot" id="burgerBtn"  role="button"',
    '<div class="beta-dot" id="burgerBtn" onclick="window.openBurgerMenu()" role="button"'
)

# 2. Ajouter console.log après la définition de openBurgerMenu
content = content.replace(
    'window.openBurgerMenu = function() {',
    '''window.openBurgerMenu = function() {
                    console.log('🍔 openBurgerMenu appelée!');'''
)

# 3. Ajouter console.log pour vérifier que la fonction est définie
content = content.replace(
    'window.closeBurgerMenu = function() {',
    '''console.log('✅ openBurgerMenu définie:', typeof window.openBurgerMenu);
                window.closeBurgerMenu = function() {'''
)

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ onclick ajouté au bouton (avec window.openBurgerMenu())")
print("✅ console.log ajoutés pour debug")
print("")
print("🔍 Dans Safari Console, vous devriez voir:")
print("   - '✅ openBurgerMenu définie: function'")
print("   - '🍔 openBurgerMenu appelée!' quand vous cliquez")
