path = 'templates/menu.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

idx_start = content.find("// Rafraîchir quand la page redevient visible (retour d'un onglet, retour d'app mobile)")
idx_end   = content.find('// Écouter les messages du Service Worker', idx_start)

old_block = content[idx_start:idx_end]

new_block = (
    "// Mémoriser quand la page passe en arrière-plan\n"
    "                var _hiddenAt = 0;\n"
    "                document.addEventListener('visibilitychange', function() {\n"
    "                    if (document.visibilityState === 'hidden') {\n"
    "                        _hiddenAt = Date.now();\n"
    "                    }\n"
    "                    if (document.visibilityState === 'visible') {\n"
    "                        var hiddenMs = _hiddenAt > 0 ? Date.now() - _hiddenAt : 0;\n"
    "                        console.log('🔄 Page redevenue visible, absente ' + hiddenMs + 'ms');\n"
    "                        // Si absente > 30s (push reçu, changement d'appli...) :\n"
    "                        // recharger depuis le serveur -> Jinja2 recalcule les badges\n"
    "                        if (hiddenMs > 30000) {\n"
    "                            console.log('🔄 Absence longue -> rechargement complet');\n"
    "                            window.location.reload();\n"
    "                            return;\n"
    "                        }\n"
    "                        // Absence courte : rafraichir via fetch (reseau dispo)\n"
    "                        if (window.refreshAllBadges) window.refreshAllBadges();\n"
    "                        if (window.refreshMissionDots) window.refreshMissionDots();\n"
    "                        if (typeof updatePlayersPointsMenu === 'function') updatePlayersPointsMenu();\n"
    "                        // 1 retry a 1.5s au cas ou le reseau est lent\n"
    "                        setTimeout(function() {\n"
    "                            if (window.refreshAllBadges) window.refreshAllBadges();\n"
    "                        }, 1500);\n"
    "                    }\n"
    "                });\n"
    "                "
)

content = content[:idx_start] + new_block + content[idx_end:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('OK - bloc remplace, longueur fichier:', len(content))
