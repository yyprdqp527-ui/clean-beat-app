#!/usr/bin/env python3
"""
Désactive les cw-tab-badges (header) sans toucher à la barre nav du bas ni aux dots isométriques.
- CSS : cache #messages-nav-badge et #courses-nav-badge
- JS : supprime leurs mises à jour
- reminder_added / reminder_toggle → mettent à jour bottomNavCoursesBadge à la place
"""

PATH = 'templates/menu.html'

with open(PATH, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# ─── 1. CSS : masquer les deux badges du header CW ──────────────────────────
OLD_CSS = '.cw-tab-badge {'
NEW_CSS = (
    '/* Badges du header CW masqués — remplacés par la barre nav fixe du bas */\n'
    '    #messages-nav-badge, #courses-nav-badge { display: none !important; }\n'
    '    .cw-tab-badge {'
)
if OLD_CSS in content and '#messages-nav-badge, #courses-nav-badge' not in content:
    content = content.replace(OLD_CSS, NEW_CSS, 1)
    changes += 1
    print('✅ CSS : badges CW header masqués')
else:
    print('⚠️  CSS : déjà modifié ou cible introuvable')

# ─── 2. JS : supprimer la mise à jour de #messages-nav-badge ────────────────
OLD_MSG_JS = (
    '                    // Onglet Messagerie dans la nav du bas\n'
    "                    var _msgB = document.getElementById('messages-nav-badge');\n"
    '                    if (_msgB) {\n'
    "                        if (count > 0) { _msgB.textContent = count < 100 ? count : '99+'; _msgB.style.display = ''; }\n"
    "                        else { _msgB.style.display = 'none'; }\n"
    '                    }\n'
)
if OLD_MSG_JS in content:
    content = content.replace(OLD_MSG_JS, '', 1)
    changes += 1
    print('✅ JS : suppression mise à jour #messages-nav-badge')
else:
    print('⚠️  JS messages-nav-badge : texte introuvable')

# ─── 3. JS reminder_added : rediriger vers bottomNavCoursesBadge ─────────────
OLD_ADDED = (
    "                        // Badge courses : badge mis à jour quand un article est ajouté (pour tous les joueurs)\n"
    "                        socket.on('reminder_added', function(data) {\n"
    "                            var badge = document.getElementById('courses-nav-badge');\n"
    '                            if (badge) {\n'
    '                                var cnt = data.pending_count || 0;\n'
    "                                if (cnt > 0) { badge.textContent = cnt < 100 ? cnt : '99+'; badge.style.display = ''; }\n"
    "                                else { badge.style.display = 'none'; }\n"
    '                            }\n'
    '                        });\n'
)
NEW_ADDED = (
    "                        // Badge courses barre nav bas : article ajouté\n"
    "                        socket.on('reminder_added', function(data) {\n"
    "                            var cnt = data.pending_count || 0;\n"
    "                            var b = document.getElementById('bottomNavCoursesBadge');\n"
    "                            if (b) {\n"
    "                                if (cnt > 0) { b.textContent = cnt < 100 ? cnt : '99+'; b.style.display = 'flex'; }\n"
    "                                else { b.style.display = 'none'; }\n"
    '                            }\n'
    '                        });\n'
)
if OLD_ADDED in content:
    content = content.replace(OLD_ADDED, NEW_ADDED, 1)
    changes += 1
    print('✅ JS : reminder_added → bottomNavCoursesBadge')
else:
    print('⚠️  JS reminder_added : texte introuvable')

# ─── 4. JS reminder_toggle : rediriger vers bottomNavCoursesBadge ────────────
OLD_TOGGLE = (
    "                        // Badge courses : badge mis à jour quand un article est coché ou décoché\n"
    "                        socket.on('reminder_toggle', function(data) {\n"
    "                            var badge = document.getElementById('courses-nav-badge');\n"
    '                            if (badge) {\n'
    '                                var cnt = data.pending_count || 0;\n'
    "                                if (cnt > 0) { badge.textContent = cnt < 100 ? cnt : '99+'; badge.style.display = ''; }\n"
    "                                else { badge.style.display = 'none'; }\n"
    '                            }\n'
    '                        });\n'
)
NEW_TOGGLE = (
    "                        // Badge courses barre nav bas : article coché/décoché\n"
    "                        socket.on('reminder_toggle', function(data) {\n"
    "                            var cnt = data.pending_count || 0;\n"
    "                            var b = document.getElementById('bottomNavCoursesBadge');\n"
    "                            if (b) {\n"
    "                                if (cnt > 0) { b.textContent = cnt < 100 ? cnt : '99+'; b.style.display = 'flex'; }\n"
    "                                else { b.style.display = 'none'; }\n"
    '                            }\n'
    '                        });\n'
)
if OLD_TOGGLE in content:
    content = content.replace(OLD_TOGGLE, NEW_TOGGLE, 1)
    changes += 1
    print('✅ JS : reminder_toggle → bottomNavCoursesBadge')
else:
    print('⚠️  JS reminder_toggle : texte introuvable')

# ─── 5. refreshAllBadges : supprimer le bloc #courses-nav-badge ──────────────
OLD_REFRESH = (
    "                            // Badge courses nav (\U0001f6d2 articles \xe0 acheter)\n"
    "                            var _cp = counts.courses_pending_count || 0;\n"
    "                            var _cNavBadge = document.getElementById('courses-nav-badge');\n"
    '                            if (_cNavBadge) {\n'
    "                                if (_cp > 0) { _cNavBadge.textContent = _cp < 100 ? _cp : '99+'; _cNavBadge.style.display = ''; }\n"
    "                                else { _cNavBadge.style.display = 'none'; }\n"
    '                            }\n'
    '                            // Badge courses barre nav fixe du bas\n'
)
NEW_REFRESH = (
    "                            // Badge courses barre nav fixe du bas\n"
    "                            var _cp = counts.courses_pending_count || 0;\n"
)
if OLD_REFRESH in content:
    content = content.replace(OLD_REFRESH, NEW_REFRESH, 1)
    changes += 1
    print('✅ JS : refreshAllBadges — bloc courses-nav-badge supprimé')
else:
    print('⚠️  JS refreshAllBadges courses-nav-badge : texte introuvable')

# ─── Écriture ─────────────────────────────────────────────────────────────────
with open(PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n{changes}/5 changements appliqués → {PATH}')
