#!/usr/bin/env python3
"""Vérification finale du fichier menu.html"""
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    s = f.read()

dead = ['updateUnreadBySender', 'updateChildrenBadges', 'avatar-notification-badge',
        'burger-nav-icon .notification-badge', 'applyAvatarUnreadBadges', '__unreadBySender']
for kw in dead:
    c = s.count(kw)
    print(f'{"✅" if c==0 else "⚠️  "+str(c)} {kw}')

fixes = ['refreshAllBadges(_attempt)', 'refreshMissionDots(_attempt)', 'event.persisted']
for fn in fixes:
    print(f'{"✅" if fn in s else "❌"} {fn}')

print(f'\nLignes: {s.count(chr(10))}')

# Vérifier que les fonctions encore appelées sont définies
import re
for fn in ['updateUnreadBadge', 'updateCoursesNavBadge', 'refreshAllBadges', 'refreshMissionDots',
           'updateAppBadge', 'markTypeRead', 'markBabyViewed', 'playMessageSound']:
    defs = len(re.findall(r'function\s+' + fn + r'\s*\(', s))
    calls = s.count(fn + '(') - defs
    status = '✅' if defs > 0 else '❌'
    print(f'  {status} {fn}: {defs} def, {calls} appel(s)')
