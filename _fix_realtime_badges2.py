#!/usr/bin/env python3
"""
Fix critique : badges ne se mettent pas à jour en temps réel.
- Expose refreshAllBadges comme window.refreshAllBadges
- Ajoute un setInterval dans le même scope que les fonctions badge
- Ajoute refreshMissionDots dans les deux intervalles
- Unifie les appels typeof pour utiliser window.
"""

PATH = 'templates/menu.html'
with open(PATH, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# ─── 1. function refreshAllBadges() → window.refreshAllBadges = function() ──
OLD_DEF = 'function refreshAllBadges() {\n'
NEW_DEF = 'window.refreshAllBadges = function() {\n'
if OLD_DEF in content:
    content = content.replace(OLD_DEF, NEW_DEF, 1)
    changes += 1
    print('✅ refreshAllBadges → window.refreshAllBadges')
else:
    print('⚠️  refreshAllBadges définition : introuvable')

# ─── 2. Fermeture : les 2 premiers } seuls à 16sp juste après refreshAllBadges ─
# Trouver la fermeture correcte (le } à 16sp qui clôt refreshAllBadges)
# On sait que c'est à L6083, juste avant "// 🧪 Fonction de test"
OLD_CLOSE = '                }\n                \n                // 🧪 Fonction de test manuelle'
NEW_CLOSE = '                };\n                \n                // 🧪 Fonction de test manuelle'
if OLD_CLOSE in content:
    content = content.replace(OLD_CLOSE, NEW_CLOSE, 1)
    changes += 1
    print('✅ Fermeture refreshAllBadges : } → };')
else:
    print('⚠️  Fermeture refreshAllBadges : texte introuvable')

# ─── 3. Remplacer le DOMContentLoaded badge poll pour ajouter un intervalle ───
OLD_DCL = (
    '                // Rafraîchir aussi au DOMContentLoaded (sécurité)\n'
    '                document.addEventListener(\'DOMContentLoaded\', function() {\n'
    '                    refreshAllBadges();\n'
    '                    refreshMissionDots();\n'
    '                });\n'
)
NEW_DCL = (
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
if OLD_DCL in content:
    content = content.replace(OLD_DCL, NEW_DCL, 1)
    changes += 1
    print('✅ DOMContentLoaded badge : polling 5s ajouté')
else:
    print('⚠️  DOMContentLoaded badge : texte introuvable')

# ─── 4. Appels immédiats : refreshAllBadges() / refreshMissionDots() → window. ─
OLD_IMM = (
    '                //  Appel IMMÉDIAT (avant même DOMContentLoaded) pour corriger les badges ASAP\n'
    '                refreshAllBadges();\n'
    '                refreshMissionDots();\n'
)
NEW_IMM = (
    '                //  Appel IMMÉDIAT (avant même DOMContentLoaded) pour corriger les badges ASAP\n'
    '                if (document.readyState !== \'loading\') {\n'
    '                    if (window.refreshAllBadges) window.refreshAllBadges();\n'
    '                    if (window.refreshMissionDots) window.refreshMissionDots();\n'
    '                }\n'
)
if OLD_IMM in content:
    content = content.replace(OLD_IMM, NEW_IMM, 1)
    changes += 1
    print('✅ Appels immédiats → window. + guard readyState')
else:
    print('⚠️  Appels immédiats : texte introuvable')

# ─── 5. Polling L4323 (script différent) → window.refreshAllBadges ──────────
OLD_POLL = (
    '                    // Rafraîchir les badges toutes les 5 secondes aussi\n'
    '                    const badgeUpdateInterval = setInterval(function() {\n'
    "                        if (typeof refreshAllBadges === 'function') refreshAllBadges();\n"
    '                    }, 5000);\n'
)
NEW_POLL = (
    '                    // Rafraîchir les badges toutes les 5 secondes aussi\n'
    '                    const badgeUpdateInterval = setInterval(function() {\n'
    '                        if (window.refreshAllBadges) window.refreshAllBadges();\n'
    '                        if (window.refreshMissionDots) window.refreshMissionDots();\n'
    '                    }, 5000);\n'
)
if OLD_POLL in content:
    content = content.replace(OLD_POLL, NEW_POLL, 1)
    changes += 1
    print('✅ Polling L4323 → window.refreshAllBadges + refreshMissionDots')
else:
    print('⚠️  Polling L4323 : texte introuvable')

# ─── 6. setTimeout 500ms (L4329) → window.refreshAllBadges ─────────────────
OLD_TO = "                    setTimeout(function() { if (typeof refreshAllBadges === 'function') refreshAllBadges(); }, 500);\n"
NEW_TO = "                    setTimeout(function() { if (window.refreshAllBadges) window.refreshAllBadges(); }, 500);\n"
if OLD_TO in content:
    content = content.replace(OLD_TO, NEW_TO, 1)
    changes += 1
    print('✅ setTimeout 500ms → window.refreshAllBadges')
else:
    print('⚠️  setTimeout 500ms : texte introuvable')

# ─── 7. house_badge_refresh socket handler → window. ───────────────────────
OLD_WS = (
    "                        socket.on('house_badge_refresh', function(data) {\n"
    '                            refreshAllBadges();\n'
    "                            if (data.message_type === 'task_added') refreshMissionDots();\n"
    '                        });\n'
)
NEW_WS = (
    "                        socket.on('house_badge_refresh', function(data) {\n"
    '                            if (window.refreshAllBadges) window.refreshAllBadges();\n'
    "                            if (window.refreshMissionDots) window.refreshMissionDots();\n"
    '                        });\n'
)
if OLD_WS in content:
    content = content.replace(OLD_WS, NEW_WS, 1)
    changes += 1
    print('✅ house_badge_refresh → window.refreshAllBadges + refreshMissionDots')
else:
    print('⚠️  house_badge_refresh : texte introuvable')

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n{changes}/7 changements appliqués → {PATH}')
