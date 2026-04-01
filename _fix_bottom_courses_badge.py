#!/usr/bin/env python3
"""Fix : ajoute la mise à jour du badge bottomNavCoursesBadge dans refreshAllBadges()"""
import re

path = 'templates/menu.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

OLD = (
    "                            // Badge courses nav (\U0001f6d2 articles \xe0 acheter)\n"
    "                            var _cNavBadge = document.getElementById('courses-nav-badge');\n"
    "                            if (_cNavBadge) {\n"
    "                                var _cp = counts.courses_pending_count || 0;\n"
    "                                if (_cp > 0) { _cNavBadge.textContent = _cp < 100 ? _cp : '99+'; _cNavBadge.style.display = ''; }\n"
    "                                else { _cNavBadge.style.display = 'none'; }\n"
    "                            }\n"
    "                            // Badge b\xe9b\xe9 sur la room card"
)

NEW = (
    "                            // Badge courses nav (\U0001f6d2 articles \xe0 acheter)\n"
    "                            var _cp = counts.courses_pending_count || 0;\n"
    "                            var _cNavBadge = document.getElementById('courses-nav-badge');\n"
    "                            if (_cNavBadge) {\n"
    "                                if (_cp > 0) { _cNavBadge.textContent = _cp < 100 ? _cp : '99+'; _cNavBadge.style.display = ''; }\n"
    "                                else { _cNavBadge.style.display = 'none'; }\n"
    "                            }\n"
    "                            // Badge courses barre nav fixe du bas\n"
    "                            var _cBottomBadge = document.getElementById('bottomNavCoursesBadge');\n"
    "                            if (_cBottomBadge) {\n"
    "                                if (_cp > 0) { _cBottomBadge.textContent = _cp < 100 ? _cp : '99+'; _cBottomBadge.style.display = 'flex'; }\n"
    "                                else { _cBottomBadge.style.display = 'none'; }\n"
    "                            }\n"
    "                            // Badge b\xe9b\xe9 sur la room card"
)

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ bottomNavCoursesBadge ajouté dans refreshAllBadges()")
else:
    print("❌ Texte cible introuvable — vérifier l'indentation ou le contenu")
