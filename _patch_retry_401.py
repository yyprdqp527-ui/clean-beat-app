#!/usr/bin/env python3
"""
Fix : retry fetch sur 401 (session cookie iOS pas encore disponible au resume bfcache)
+ allongement des retries pageshow jusqu'à 10s
"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# -------------------------------------------------------------------
# 1. Dans refreshAllBadges : retenter sur 401 (session pas encore active)
#    au lieu de retourner null silencieusement
# -------------------------------------------------------------------
old1 = (
    "                    fetch('/api/unread_counts', { cache: 'no-store', credentials: 'same-origin' })\n"
    "                        .then(function(r) { if (!r.ok) return null; return r.json(); })\n"
    "                        .then(function(counts) {\n"
    "                            if (!counts || counts.error) return;"
)
new1 = (
    "                    fetch('/api/unread_counts', { cache: 'no-store', credentials: 'same-origin' })\n"
    "                        .then(function(r) {\n"
    "                            // 401 = session pas encore restaurée (iOS bfcache) → on relance dans 1s\n"
    "                            if (r.status === 401) {\n"
    "                                setTimeout(function() { if (window.refreshAllBadges) window.refreshAllBadges(); }, 1000);\n"
    "                                return null;\n"
    "                            }\n"
    "                            if (!r.ok) return null;\n"
    "                            return r.json();\n"
    "                        })\n"
    "                        .then(function(counts) {\n"
    "                            if (!counts || counts.error) return;"
)

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("OK: refreshAllBadges retry 401")
else:
    print("SKIP: section refreshAllBadges non trouvée")

# -------------------------------------------------------------------
# 2. Même fix dans refreshMissionDots
# -------------------------------------------------------------------
old2 = (
    "                    fetch('/api/rooms_with_missions', { cache: 'no-store', credentials: 'same-origin' })\n"
    "                        .then(function(r) {\n"
    "                            // ⚠️ Si réseau indispo ou erreur : ne PAS écraser les pastilles Jinja\n"
    "                            if (!r.ok) return null;\n"
    "                            return r.json();\n"
    "                        })"
)
new2 = (
    "                    fetch('/api/rooms_with_missions', { cache: 'no-store', credentials: 'same-origin' })\n"
    "                        .then(function(r) {\n"
    "                            // 401 = session pas encore restaurée (iOS bfcache) → relancer dans 1s\n"
    "                            if (r.status === 401) {\n"
    "                                setTimeout(function() { if (window.refreshMissionDots) window.refreshMissionDots(); }, 1000);\n"
    "                                return null;\n"
    "                            }\n"
    "                            if (!r.ok) return null;\n"
    "                            return r.json();\n"
    "                        })"
)

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("OK: refreshMissionDots retry 401")
else:
    print("SKIP: section refreshMissionDots non trouvée")

# -------------------------------------------------------------------
# 3. pageshow : allonger les retries jusqu'à 10s (couvre iOS lent)
# -------------------------------------------------------------------
old3 = (
    "                    // Retentatives si réseau = pas encore dispo (iOS PWA réveil)\n"
    "                    [600, 1800, 4000].forEach(function(delay) {\n"
    "                        setTimeout(function() {\n"
    "                            if (window.refreshAllBadges) window.refreshAllBadges();\n"
    "                            }, delay);\n"
    "                    });"
)
new3 = (
    "                    // Retentatives progressives (iOS PWA : session cookie + réseau peuvent\n"
    "                    // prendre jusqu'à 8-10s à se rétablir après background long)\n"
    "                    [600, 1500, 3000, 5000, 8000, 12000].forEach(function(delay) {\n"
    "                        setTimeout(function() {\n"
    "                            if (window.refreshAllBadges) window.refreshAllBadges();\n"
    "                            if (window.refreshMissionDots) window.refreshMissionDots();\n"
    "                        }, delay);\n"
    "                    });"
)

if old3 in content:
    content = content.replace(old3, new3, 1)
    print("OK: pageshow retries allongés")
else:
    print("SKIP: section pageshow retries non trouvée (vérifier manuellement)")

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Sauvegarde OK")
