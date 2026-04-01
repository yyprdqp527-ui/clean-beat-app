import re

# ─── Fix 1 : menu.html visibilitychange → reload après >30s ───────────────────
path_menu = 'templates/menu.html'
with open(path_menu, encoding='utf-8') as f:
    menu = f.read()

old_vis = (
    "                // Rafraîchir quand la page redevient visible (retour d'un onglet, retour d'app mobile)\n"
    "                document.addEventListener('visibilitychange', function() {\n"
    "                    if (document.visibilityState === 'visible') {\n"
    "                        console.log('🔄 Page redevenue visible');\n"
    "                        if (window.refreshAllBadges) window.refreshAllBadges();\n"
    "                        if (window.refreshMissionDots) window.refreshMissionDots();\n"
    "                        if (typeof updatePlayersPointsMenu === 'function') updatePlayersPointsMenu();\n"
    "                        // Retry progressif : iOS peut prendre 1-5s a retablir le reseau apres background\n"
    "                        [800, 2500, 5000, 8000].forEach(function(delay) {\n"
    "                            setTimeout(function() {\n"
    "                                if (window.refreshAllBadges) window.refreshAllBadges();\n"
    "                                if (window.refreshMissionDots) window.refreshMissionDots();\n"
    "                            }, delay);\n"
    "                        });\n"
    "                    }\n"
    "                });"
)

new_vis = (
    "                // Rafraîchir quand la page redevient visible (retour d'un onglet, retour d'app mobile)\n"
    "                var _menuHiddenAt = 0;\n"
    "                document.addEventListener('visibilitychange', function() {\n"
    "                    if (document.visibilityState === 'hidden') {\n"
    "                        _menuHiddenAt = Date.now();\n"
    "                    }\n"
    "                    if (document.visibilityState === 'visible') {\n"
    "                        var _hiddenDuration = _menuHiddenAt ? (Date.now() - _menuHiddenAt) : 0;\n"
    "                        if (_hiddenDuration > 30000) {\n"
    "                            // Absent plus de 30s -> rechargement complet pour badges Jinja2 frais\n"
    "                            console.log('🔄 Retour background ' + Math.round(_hiddenDuration/1000) + 's -> rechargement');\n"
    "                            window.location.reload();\n"
    "                            return;\n"
    "                        }\n"
    "                        // Bref passage en background -> simple refresh suffit\n"
    "                        console.log('🔄 Page redevenue visible (background court)');\n"
    "                        if (window.refreshAllBadges) window.refreshAllBadges();\n"
    "                        if (window.refreshMissionDots) window.refreshMissionDots();\n"
    "                        if (typeof updatePlayersPointsMenu === 'function') updatePlayersPointsMenu();\n"
    "                    }\n"
    "                });"
)

if old_vis in menu:
    menu = menu.replace(old_vis, new_vis, 1)
    with open(path_menu, 'w', encoding='utf-8') as f:
        f.write(menu)
    print('✅ Fix 1 appliqué : visibilitychange reload >30s dans menu.html')
else:
    print('❌ Fix 1 : texte non trouvé dans menu.html')
    idx = menu.find("visibilitychange")
    print('Contexte trouvé à idx', idx, ':', repr(menu[idx:idx+100]))

# ─── Fix 2 : comments.html — exclure courses+missions du badge icône ──────────
path_comments = 'templates/comments.html'
with open(path_comments, encoding='utf-8') as f:
    comments = f.read()

old_badge = (
    "                var total = ((c.unread_received||0) > 0 ? 1 : 0)\n"
    "                          + ((c.unread_baby||0) > 0 ? 1 : 0)\n"
    "                          + ((c.courses_pending_count||0) > 0 ? 1 : 0)\n"
    "                          + ((c.pending_missions_count||0) > 0 ? 1 : 0);"
)

new_badge = (
    "                // Badge icone : seulement messages + bébé (pas courses/missions = tâches permanentes)\n"
    "                var total = ((c.unread_received||0) > 0 ? 1 : 0)\n"
    "                          + ((c.unread_baby||0) > 0 ? 1 : 0);"
)

if old_badge in comments:
    comments = comments.replace(old_badge, new_badge, 1)
    with open(path_comments, 'w', encoding='utf-8') as f:
        f.write(comments)
    print('✅ Fix 2 appliqué : badge comments.html sans courses/missions')
else:
    print('❌ Fix 2 : texte non trouvé dans comments.html')
    idx = comments.find('refreshNativeBadge')
    print('Contexte:', repr(comments[idx:idx+300]))
