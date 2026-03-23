#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacer notre script burger par une version avec event listeners
old_burger_script = """<script>
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
</script>"""

new_burger_script = """<script>
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
    console.log('🍔 closeBurgerMenu appelée!');
    var overlay = document.getElementById('burgerOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }
};

// Attendre que le DOM soit chargé pour ajouter les event listeners
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Fonctions burger définies');
    
    // Bouton close (croix)
    var closeBtn = document.getElementById('burgerClose');
    if (closeBtn) {
        closeBtn.addEventListener('click', window.closeBurgerMenu);
        console.log('✅ Event listener ajouté au bouton close');
    }
    
    // Clic sur l'overlay (ferme si on clique en dehors)
    var overlay = document.getElementById('burgerOverlay');
    if (overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                window.closeBurgerMenu();
            }
        });
        console.log('✅ Event listener ajouté à l\'overlay');
    }
    
    // Touche Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            var overlay = document.getElementById('burgerOverlay');
            if (overlay && overlay.classList.contains('active')) {
                window.closeBurgerMenu();
            }
        }
    });
});
</script>"""

if old_burger_script in content:
    content = content.replace(old_burger_script, new_burger_script)
    print("✅ Script burger mis à jour avec event listeners")
    print("   - Croix (burgerClose)")
    print("   - Clic sur overlay")
    print("   - Touche Escape")
else:
    print("❌ Script burger original non trouvé")

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("🎯 Le bouton close devrait maintenant fermer le menu!")
