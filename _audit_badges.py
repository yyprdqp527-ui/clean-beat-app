#!/usr/bin/env python3
# Audit complet du systeme de badges PWA
import json

c = open('templates/menu.html', encoding='utf-8').read()
sw = open('static/sw.js', encoding='utf-8').read()
m = json.load(open('static/manifest.json', encoding='utf-8'))

checks = [
    ('manifest display:standalone',     m.get('display') == 'standalone'),
    ('manifest start_url:/menu',        m.get('start_url') == '/menu'),
    ('SW skipWaiting',                  'skipWaiting()' in sw),
    ('SW clients.claim',                'clients.claim()' in sw),
    ('SW setAppBadge on push',          'setAppBadge(badgeCount)' in sw),
    ('SW REFRESH_BADGES postMessage',   'REFRESH_BADGES' in sw),
    ('updateUnreadBadge definie',       'function updateUnreadBadge' in c),
    ('updateCoursesNavBadge definie',   'function updateCoursesNavBadge' in c),
    ('updateAppBadge definie',          'function updateAppBadge' in c),
    ('refreshAllBadges definie',        'function refreshAllBadges' in c),
    ('refreshMissionDots definie',      'function refreshMissionDots' in c),
    ('DOM bottomNavMessagesBadge',      'id="bottomNavMessagesBadge"' in c),
    ('DOM bottomNavCoursesBadge',       'id="bottomNavCoursesBadge"' in c),
    ('DOM room-baby-dot',               'id="room-baby-dot"' in c),
    ('IIFE baby getElementById',        "getElementById('room-baby-dot')" in c),
    ('IIFE missions selecteur correct', '.room-card-visual[data-category]' in c and '.room-mission-dot' in c),
    ('IIFE badge total 4 types',        '_sc.courses_pending_count' in c and '_sc.pending_missions_count' in c),
    ('sessionStorage missions Jinja2',  'pending_missions_count: {{ rooms_with_new_missions' in c),
    ('PWA badge app total 4 types',     'courses_pending_count || 0)' in c and 'pending_missions_count || 0)' in c),
    ('clearAppBadge si count=0 seul',   'clearAppBadge' in c and 'count > 0' in c),
    ('bfcache reload complet',          'event.persisted' in c and 'location.reload()' in c),
    ('visibilitychange reload >30s',    'hiddenMs > 30000' in c),
    ('REFRESH_BADGES -> refreshAll',    'REFRESH_BADGES' in c and 'refreshAllBadges' in c),
    ('NAVIGATE_TO -> window.location',  'NAVIGATE_TO' in c and 'window.location.href' in c),
]

all_ok = True
for label, result in checks:
    status = 'OK  ' if result else 'FAIL'
    if not result:
        all_ok = False
    print(f'[{status}]  {label}')

print()
if all_ok:
    print('BADGE SYSTEM 100% OK - pret pour commit Render')
else:
    print('ECHECS DETECTES - voir ci-dessus')
