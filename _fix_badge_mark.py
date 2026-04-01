#!/usr/bin/env python3
"""Ajoute markTypeRead() dans menu.html pour décrémenter le badge icône app."""

path = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html'

f = open(path, 'r', encoding='utf-8')
content = f.read()
f.close()

# Chaîne exacte à remplacer (ligne 6071-6072 du fichier original)
old = (
    "                // Rafraîchir aussi au DOMContentLoaded (sécurité)\n"
    "                document.addEventListener('DOMContentLoaded', function() { refreshAllBadges(); refreshMissionDots(); });\n"
)

new = (
    "                // Marquer task_added comme lu après chargement\n"
    "                // Puis recalculer les badges -> le badge icône app se décrémente\n"
    "                function markTypeRead(type) {\n"
    "                    fetch('/api/mark_type_read', {\n"
    "                        method: 'POST',\n"
    "                        headers: {'Content-Type': 'application/json'},\n"
    "                        body: JSON.stringify({type: type})\n"
    "                    }).then(function() {\n"
    "                        refreshAllBadges();\n"
    "                    }).catch(function(){});\n"
    "                }\n"
    "\n"
    "                // Rafraîchir aussi au DOMContentLoaded (sécurité)\n"
    "                document.addEventListener('DOMContentLoaded', function() {\n"
    "                    refreshAllBadges();\n"
    "                    refreshMissionDots();\n"
    "                    // Marquer task_added comme lu 1.5s après chargement -> badge icône mis à jour\n"
    "                    setTimeout(function() { markTypeRead('task_added'); }, 1500);\n"
    "                });\n"
)

count = content.count(old)
print(f"Occurrences trouvées: {count}")

if count == 1:
    content = content.replace(old, new)
    f = open(path, 'w', encoding='utf-8')
    f.write(content)
    f.close()
    print("OK: fichier modifié")
    # Vérification
    f2 = open(path, 'r', encoding='utf-8')
    c2 = f2.read()
    f2.close()
    print("markTypeRead présent:", 'markTypeRead' in c2)
else:
    print("ERREUR: chaîne non trouvée ou ambiguë")
    idx = content.find("Rafraîchir aussi au DOMContentLoaded")
    if idx >= 0:
        print("Contexte trouvé:")
        print(repr(content[idx-50:idx+200]))
