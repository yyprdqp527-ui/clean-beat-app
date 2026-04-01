#!/usr/bin/env python3
"""Retire courses+missions du badge icône PWA (gardés uniquement dans la nav interne)"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = (
    "                            // 4. Badge icône PWA : 1 par type présent (max 4)\n"
    "                            var total = ((counts.unread_received   || 0) > 0 ? 1 : 0)\n"
    "                                      + ((counts.unread_baby        || 0) > 0 ? 1 : 0)\n"
    "                                      + ((counts.courses_pending_count || 0) > 0 ? 1 : 0)\n"
    "                                      + ((counts.pending_missions_count || 0) > 0 ? 1 : 0);\n"
    "                            updateAppBadge(total);"
)

new = (
    "                            // 4. Badge icone PWA : seulement messages + bebe non lus\n"
    "                            // courses et missions EXCLUS : ce sont des taches en attente,\n"
    "                            // pas des notifications nouvelles -> badge permanent sinon\n"
    "                            var total = ((counts.unread_received || 0) > 0 ? 1 : 0)\n"
    "                                      + ((counts.unread_baby    || 0) > 0 ? 1 : 0);\n"
    "                            updateAppBadge(total);"
)

if old in content:
    content = content.replace(old, new, 1)
    print("OK: badge PWA corrige")
else:
    print("SKIP: section deja patchee ou non trouvee")

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Sauvegarde OK")
