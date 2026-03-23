#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trouver la ligne <body>
body_line = None
for i, line in enumerate(lines):
    if '<body>' in line:
        body_line = i
        break

if not body_line:
    print("❌ <body> non trouvé")
    exit(1)

# Insérer un script simple au début qui définit openBurgerMenu
burger_script = """
<script>
// 🍔 MENU BURGER - Définition globale immédiate
window.openBurgerMenu = function() {
    console.log('🍔 openBurgerMenu appelée!');
    var overlay = document.getElementById('burgerOverlay');
    if (overlay) {
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    } else {
        console.error('🔴 burgerOverlay not found!');
    }
};

window.closeBurgerMenu = function() {
    var overlay = document.getElementById('burgerOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }
};

console.log('✅ Fonctions burger définies:', typeof window.openBurgerMenu, typeof window.closeBurgerMenu);
</script>

"""

# Insérer après <body>
lines.insert(body_line + 1, burger_script)

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✅ Script burger inséré après <body> (ligne {body_line +1})")
print("🎯 window.openBurgerMenu sera définie immédiatement au chargement")
print("\n⚠️  Note: L'ancienne définition ligne ~4904 existe toujours")
print("   mais elle sera écrasée par celle-ci (définie en premier)")
