#!/usr/bin/env python3
"""Patch menu.html : ajoute NAVIGATE_TO handler + retries réseau iOS"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# -------------------------------------------------------------------
# 1. Ajouter NAVIGATE_TO dans le listener Service Worker
# -------------------------------------------------------------------
old_sw = (
    "// Écouter les messages du Service Worker (ex: REFRESH_BADGES après push)\n"
    "                if ('serviceWorker' in navigator) {\n"
    "                    navigator.serviceWorker.addEventListener('message', function(event) {\n"
    "                        if (event.data && event.data.type === 'REFRESH_BADGES') {\n"
    "                            console.log('SW: Rafraîchissement des badges demandé');\n"
    "                            window.refreshAllBadges();\n"
    "                        }\n"
    "                    });\n"
    "                }"
)

new_sw = (
    "// Écouter les messages du Service Worker (ex: REFRESH_BADGES après push)\n"
    "                if ('serviceWorker' in navigator) {\n"
    "                    navigator.serviceWorker.addEventListener('message', function(event) {\n"
    "                        if (event.data && event.data.type === 'REFRESH_BADGES') {\n"
    "                            console.log('SW: Rafraîchissement des badges demandé');\n"
    "                            window.refreshAllBadges();\n"
    "                            if (window.refreshMissionDots) window.refreshMissionDots();\n"
    "                        }\n"
    "                        // NAVIGATE_TO : déclenché par notificationclick dans sw.js\n"
    "                        // Rechargement complet -> Jinja2 rend les badges frais (iOS + Android)\n"
    "                        if (event.data && event.data.type === 'NAVIGATE_TO') {\n"
    "                            var targetUrl = event.data.url || '/menu';\n"
    "                            console.log('SW: Navigation vers', targetUrl);\n"
    "                            window.location.href = targetUrl;\n"
    "                        }\n"
    "                    });\n"
    "                }"
)

if old_sw in content:
    content = content.replace(old_sw, new_sw, 1)
    print("OK: Listener SW mis a jour (NAVIGATE_TO ajoute)")
else:
    print("SKIP: Section SW non trouvee (deja patchee?)")

# -------------------------------------------------------------------
# 2. Ajouter retries réseau iOS dans visibilitychange
# -------------------------------------------------------------------
old_vis = (
    "                        if (window.refreshAllBadges) window.refreshAllBadges();\n"
    "                        if (window.refreshMissionDots) window.refreshMissionDots();\n"
    "                        if (typeof updatePlayersPointsMenu === 'function') updatePlayersPointsMenu();\n"
    "                    }\n"
    "                });\n"
    "                // Écouter les messages du Service Worker"
)

new_vis = (
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
    "                });\n"
    "                // Écouter les messages du Service Worker"
)

if old_vis in content:
    content = content.replace(old_vis, new_vis, 1)
    print("OK: Retries visibilitychange mis a jour")
else:
    print("SKIP: Section visibilitychange non trouvee (deja patchee?)")

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fichier sauvegarde.")
