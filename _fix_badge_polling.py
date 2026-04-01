#!/usr/bin/env python3
"""
Fix : badges courses (et tous badges) ne se mettent pas à jour en temps réel.
Causes :
  1. setInterval enfermé dans DOMContentLoaded qui ne tire jamais (DOM déjà chargé)
  2. guard readyState inutilement restrictif
  Solution : appels directs + setInterval direct (les fonctions sont définies au-dessus)
"""

PATH = 'templates/menu.html'
with open(PATH, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# ─── 1. Remplacer le bloc "appel immédiat + DOMContentLoaded + setInterval" ──
OLD = (
    '                //  Appel IMMÉDIAT (avant même DOMContentLoaded) pour corriger les badges ASAP\n'
    '                if (document.readyState !== \'loading\') {\n'
    '                    if (window.refreshAllBadges) window.refreshAllBadges();\n'
    '                    if (window.refreshMissionDots) window.refreshMissionDots();\n'
    '                }\n'
    '                \n'
    '                // Marquer task_added comme lu après chargement\n'
    '                // Puis recalculer les badges -> le badge icône app se décrémente\n'
    '                function markTypeRead(type) {\n'
    '                    fetch(\'/api/mark_type_read\', {\n'
    '                        method: \'POST\',\n'
    '                        headers: {\'Content-Type\': \'application/json\'},\n'
    '                        body: JSON.stringify({type: type})\n'
    '                    }).then(function() {\n'
    '                        refreshAllBadges();\n'
    '                    }).catch(function(){});\n'
    '                }\n'
    '\n'
    '                // Rafraîchir aussi au DOMContentLoaded (sécurité)\n'
    '                document.addEventListener(\'DOMContentLoaded\', function() {\n'
    '                    if (window.refreshAllBadges) window.refreshAllBadges();\n'
    '                    if (window.refreshMissionDots) window.refreshMissionDots();\n'
    '                    // Polling fiable dans ce scope (où les fonctions sont définies)\n'
    '                    setInterval(function() {\n'
    '                        if (window.refreshAllBadges) window.refreshAllBadges();\n'
    '                        if (window.refreshMissionDots) window.refreshMissionDots();\n'
    '                    }, 5000);\n'
    '                });\n'
)

NEW = (
    '                //  Appel IMMÉDIAT — badges corrigés dès l\'exécution du script\n'
    '                window.refreshAllBadges();\n'
    '                window.refreshMissionDots();\n'
    '\n'
    '                // Polling toutes les 5s dans ce scope (fonctions définies ci-dessus)\n'
    '                setInterval(function() {\n'
    '                    window.refreshAllBadges();\n'
    '                    window.refreshMissionDots();\n'
    '                }, 5000);\n'
    '\n'
    '                // Marquer task_added comme lu après chargement\n'
    '                // Puis recalculer les badges -> le badge icône app se décrémente\n'
    '                function markTypeRead(type) {\n'
    '                    fetch(\'/api/mark_type_read\', {\n'
    '                        method: \'POST\',\n'
    '                        headers: {\'Content-Type\': \'application/json\'},\n'
    '                        body: JSON.stringify({type: type})\n'
    '                    }).then(function() {\n'
    '                        window.refreshAllBadges();\n'
    '                    }).catch(function(){});\n'
    '                }\n'
    '\n'
    '                // Rafraîchir aussi au DOMContentLoaded si script chargé très tôt\n'
    '                if (document.readyState === \'loading\') {\n'
    '                    document.addEventListener(\'DOMContentLoaded\', function() {\n'
    '                        window.refreshAllBadges();\n'
    '                        window.refreshMissionDots();\n'
    '                    });\n'
    '                }\n'
)

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    changes += 1
    print('✅ Bloc polling réécrit (appels directs + setInterval immédiat)')
else:
    print('❌ Bloc cible introuvable — tentative bloc partiel...')
    # Essayer de trouver juste les parties clés
    OLD2 = (
        '                if (document.readyState !== \'loading\') {\n'
        '                    if (window.refreshAllBadges) window.refreshAllBadges();\n'
        '                    if (window.refreshMissionDots) window.refreshMissionDots();\n'
        '                }\n'
    )
    NEW2 = (
        '                window.refreshAllBadges();\n'
        '                window.refreshMissionDots();\n'
    )
    if OLD2 in content:
        content = content.replace(OLD2, NEW2, 1)
        changes += 1
        print('✅ Appel immédiat corrigé (guard readyState supprimé)')
    else:
        print('❌ Appel immédiat introuvable')

    OLD3 = (
        '                // Rafraîchir aussi au DOMContentLoaded (sécurité)\n'
        '                document.addEventListener(\'DOMContentLoaded\', function() {\n'
        '                    if (window.refreshAllBadges) window.refreshAllBadges();\n'
        '                    if (window.refreshMissionDots) window.refreshMissionDots();\n'
        '                    // Polling fiable dans ce scope (où les fonctions sont définies)\n'
        '                    setInterval(function() {\n'
        '                        if (window.refreshAllBadges) window.refreshAllBadges();\n'
        '                        if (window.refreshMissionDots) window.refreshMissionDots();\n'
        '                    }, 5000);\n'
        '                });\n'
    )
    NEW3 = (
        '                // Polling toutes les 5s dans ce scope\n'
        '                setInterval(function() {\n'
        '                    window.refreshAllBadges();\n'
        '                    window.refreshMissionDots();\n'
        '                }, 5000);\n'
        '                // Fallback si script chargé avant DOM\n'
        '                if (document.readyState === \'loading\') {\n'
        '                    document.addEventListener(\'DOMContentLoaded\', function() {\n'
        '                        window.refreshAllBadges();\n'
        '                        window.refreshMissionDots();\n'
        '                    });\n'
        '                }\n'
    )
    if OLD3 in content:
        content = content.replace(OLD3, NEW3, 1)
        changes += 1
        print('✅ DOMContentLoaded → setInterval direct')
    else:
        print('❌ DOMContentLoaded bloc introuvable')

# ─── 2. pageshow et visibilitychange : bare → window. ──────────────────────
for bare, wref in [
    ('                    refreshAllBadges();\n                    if (typeof updatePlayersPointsMenu',
     '                    window.refreshAllBadges();\n                    if (typeof updatePlayersPointsMenu'),
]:
    if bare in content:
        content = content.replace(bare, wref)
        changes += 1
        print('✅ pageshow → window.refreshAllBadges')
    # Non bloquant

# ─── 3. SW message handler : bare → window. ─────────────────────────────────
OLD_SW = "                            refreshAllBadges();\n                        }\n                    });\n                }\n            </script>"
NEW_SW = "                            window.refreshAllBadges();\n                        }\n                    });\n                }\n            </script>"
if OLD_SW in content:
    content = content.replace(OLD_SW, NEW_SW, 1)
    changes += 1
    print('✅ SW message handler → window.refreshAllBadges')

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n{changes} changements appliqués → {PATH}')
