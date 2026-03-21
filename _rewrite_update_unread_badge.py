#!/usr/bin/env python3
"""
Réécrire la fonction updateUnreadBadge pour mettre à jour le badge du menu fixe
"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Ligne 5251 est l'index 5250 (0-based)
# Ligne 5357 est l'index 5356
START_LINE = 5250  # 0-based
END_LINE = 5356    # 0-based (inclus)

# Nouvelle fonction
NEW_FUNCTION = """                function updateUnreadBadge(count) {
                    console.log('🔔 updateUnreadBadge appelé avec count:', count);
                    
                    // 🏠 Badge icône écran d'accueil (PWA Badging API — iOS 16.4+, Android Chrome)
                    if ('setAppBadge' in navigator) {
                        if (count > 0) {
                            navigator.setAppBadge(count).catch(function(){});
                        } else {
                            navigator.clearAppBadge().catch(function(){});
                        }
                    }
                    
                    // 🍔 Mettre à jour le badge dans le menu burger (total des messages)
                    const burgerBadges = document.querySelectorAll('.burger-nav-icon .notification-badge');
                    console.log('🍔 Badges burger trouvés:', burgerBadges.length);
                    burgerBadges.forEach(badge => {
                        if (count > 0) {
                            badge.textContent = count < 100 ? count : '99+';
                            badge.style.display = 'flex';
                            console.log('✅ Badge burger affiché:', badge.textContent);
                        } else {
                            badge.style.display = 'none';
                            console.log('❌ Badge burger caché');
                        }
                    });
                    
                    // 💬 Mettre à jour le badge du bouton Messages dans le menu de navigation fixe en bas
                    const bottomNavBadge = document.getElementById('bottomNavMessagesBadge');
                    console.log('📍 Bottom nav badge trouvé:', bottomNavBadge);
                    if (bottomNavBadge) {
                        if (count > 0) {
                            bottomNavBadge.textContent = count < 100 ? count : '99+';
                            bottomNavBadge.style.display = 'flex';
                            console.log('✅ Bottom nav badge affiché:', bottomNavBadge.textContent);
                        } else {
                            bottomNavBadge.style.display = 'none';
                            console.log('❌ Bottom nav badge caché');
                        }
                    }
                }
"""

# Remplacer les lignes
new_lines = lines[:START_LINE] + [NEW_FUNCTION] + lines[END_LINE+1:]

# Sauvegarder
with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"✅ Fonction updateUnreadBadge remplacée (lignes {START_LINE+1}-{END_LINE+1})")
print(f"   Ancienne fonction: {END_LINE - START_LINE + 1} lignes")
print(f"   Nouvelle fonction: {len(NEW_FUNCTION.splitlines())} lignes")
