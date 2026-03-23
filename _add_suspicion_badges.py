#!/usr/bin/env python3
"""
Ajouter le système JavaScript de badges suspicion (loupe 🔍)
Identique aux systèmes malus et bonus existants
"""

file_path = 'templates/menu.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Vérifier si le code existe déjà
if 'loadActiveSuspicions' in content:
    print("✅ Le système de suspicions existe déjà !")
    exit(0)

# Code à insérer (copié du système malus/bonus)
new_code = '''
            <script>
            // ═══════════════════════════════════════════════════════════
            // 🔍 SYSTÈME DE SUSPICIONS — Afficher loupe sur avatars
            // ═══════════════════════════════════════════════════════════

            (function() {
                // Tracking local des suspicions émises (pour affichage immédiat)
                window._localSuspicionMap = window._localSuspicionMap || {}; // email → timestamp

                function loadActiveSuspicions() {
                    console.log('🔍 loadActiveSuspicions - Début du chargement...');
                    fetch('/api/active_suspicions')
                    .then(r => r.json())
                    .then(data => {
                        // Supprimer tous les anciens badges loupe
                        document.querySelectorAll('.loupe-badge').forEach(el => el.remove());

                        // Fusionner suspicions API + suspicions locales
                        const now = Date.now();
                        const ONE_HOUR = 60 * 60 * 1000;
                        const apiSuspicions = data.suspicions || [];
                        const allSuspicions = [...apiSuspicions];
                        
                        // Ajouter les suspicions locales non expirées qui ne sont pas déjà dans l'API
                        if (window._localSuspicionMap) {
                            Object.keys(window._localSuspicionMap).forEach(function(email) {
                                const timestamp = window._localSuspicionMap[email];
                                // Vérifier si non expiré (< 1h)
                                if (now - timestamp <= ONE_HOUR) {
                                    // Vérifier si pas déjà dans les suspicions API
                                    if (!apiSuspicions.find(s => s.email === email)) {
                                        allSuspicions.push({ email: email, name: null });
                                    }
                                } else {
                                    // Supprimer les suspicions locales expirées
                                    delete window._localSuspicionMap[email];
                                }
                            });
                        }
                        
                        console.log('🔍 loadActiveSuspicions - Suspicions actives:', allSuspicions);
                        if (allSuspicions.length === 0) return;
                        
                        // Afficher la loupe sur chaque joueur ayant une suspicion active
                        allSuspicions.forEach(s => {
                            const loupeTitle = 'Suspicion active' + (s.name ? ' : ' + s.name : '');
                            console.log('🔍 Ajout loupe pour:', s.email);
                            
                            // Header : cibler TOUS les wrappers avatar (3 sections dans le DOM)
                            document.querySelectorAll('.avatar-square-wrapper[data-player-email="' + s.email + '"]').forEach(function(avatarWrapper) {
                                avatarWrapper.style.position = 'relative';
                                const loupe = document.createElement('span');
                                loupe.className = 'loupe-badge';
                                loupe.textContent = '🔍';
                                loupe.title = loupeTitle;
                                loupe.style.cssText = 'position:absolute;top:-3px;right:-8px;font-size:18px;line-height:1;pointer-events:none;z-index:10;filter:drop-shadow(0 2px 4px rgba(255,165,0,0.5));animation:loupeBounce 0.9s ease infinite alternate;';
                                avatarWrapper.appendChild(loupe);
                            });
                        });
                    })
                    .catch(err => {
                        console.error('❌ Erreur loadActiveSuspicions:', err);
                    });
                }
                
                // Exposer la fonction sur window pour accès global
                window.loadActiveSuspicions = loadActiveSuspicions;
                
                // Anim CSS loupe bounce
                if (!document.getElementById('loupeBounceAnim')) {
                    const style = document.createElement('style');
                    style.id = 'loupeBounceAnim';
                    style.textContent = '@keyframes loupeBounce { from { transform: translateY(0) scale(1); } to { transform: translateY(-5px) scale(1.15); } }';
                    document.head.appendChild(style);
                }
                
                // Charger les suspicions au démarrage
                loadActiveSuspicions();
                // Rafraîchir toutes les 60 secondes
                setInterval(loadActiveSuspicions, 60000);
                console.log('✅ Système suspicion loupe initialisé');
            })();

            </script>

'''

# Point d'insertion : après le système bonus (après "</script>")
marker = "                console.log('\\u2705 Syst\\u00e8me bonus coeur initialis\\u00e9');\n            })();\n\n\n            </script>\n\n            \n\n<!-- ═══ BANNIÈRE INSTALLATION PWA ═══ -->"

if marker in content:
    # Insérer avant le commentaire PWA
    content = content.replace(marker, marker.replace('</script>\n\n            \n\n<!-- ═══ BANNIÈRE INSTALLATION PWA ═══ -->', '</script>' + new_code + '\n\n<!-- ═══ BANNIÈRE INSTALLATION PWA ═══ -->'))
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Système de suspicions ajouté après le système bonus !")
    print("📍 La loupe 🔍 s'affichera automatiquement toutes les 60 secondes")
    print("🎯 Position : top:-3px; right:-8px (en haut à droite de l'avatar)")
else:
    print("❌ Marqueur d'insertion non trouvé. Recherche d'une alternative...")
    # Alternative : insérer avant le commentaire PWA
    alt_marker = '\n\n<!-- ═══ BANNIÈRE INSTALLATION PWA ═══ -->'
    if alt_marker in content:
        content = content.replace(alt_marker, new_code + alt_marker)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Système de suspicions ajouté (alternative) !")
    else:
        print("❌ Impossible de trouver le point d'insertion")
        print("Cherchez manuellement : <!-- ═══ BANNIÈRE INSTALLATION PWA ═══ -->")
