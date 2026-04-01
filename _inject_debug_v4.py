#!/usr/bin/env python3
"""Injecte un bandeau de debug V4 dans menu.html pour tracer SSR→JS"""

import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Point d'insertion: juste après <body>
old = '<body>\n\n<script>\n//  MENU BURGER'
if old not in content:
    print('ERREUR: pattern non trouvé')
    exit(1)

debug_banner = '''<body>
<!-- 🔧 DEBUG V4 — trace SSR + JS step-by-step (auto-supprime 30s) -->
<div id="_dbg4" style="position:fixed;top:0;left:0;right:0;background:#1a1a2e;color:#0f0;z-index:99999;padding:6px 8px;font:bold 10px/1.4 monospace;max-height:35vh;overflow-y:auto;border-bottom:2px solid #0f0;">
SSR: MSG={{ unread_messages_count|default("?") }} BABY={{ unread_baby_tracking|default("?") }} CRS={{ courses_pending_count|default("?") }} MISS={{ rooms_with_new_missions|default({})|length }} players={{ players|length }}<br>
missions={{ rooms_with_new_missions|default({})|tojson }}<br>
<span id="_dbg4_js">JS: en attente...</span>
<button onclick="this.parentElement.remove()" style="position:absolute;top:2px;right:4px;background:#333;color:#0f0;border:1px solid #0f0;font:bold 12px monospace;cursor:pointer;padding:2px 6px;">X</button>
</div>
<script>
window._dbg4_log = function(msg) {
    var el = document.getElementById('_dbg4_js');
    if (el) el.innerHTML += '<br>' + new Date().toLocaleTimeString() + ' ' + msg;
};
setTimeout(function(){ var d=document.getElementById('_dbg4'); if(d) d.remove(); }, 30000);
</script>

<script>
//  MENU BURGER'''

content = content.replace(old, debug_banner, 1)
print('✅ Bandeau debug V4 injecté après <body>')

# Ajouter des logs dans l'IIFE pré-affichage
old_iife = "var _sm = {{ rooms_with_new_missions | tojson }};"
new_iife = """var _sm = {{ rooms_with_new_missions | tojson }};
                        if (window._dbg4_log) window._dbg4_log('IIFE: _sc=' + JSON.stringify(_sc) + ' _sm=' + JSON.stringify(_sm));"""
if old_iife in content:
    content = content.replace(old_iife, new_iife, 1)
    print('✅ Log ajouté dans IIFE pré-affichage')

# Ajouter des logs dans refreshAllBadges (après réception API)
old_refresh = "if (!counts || counts.error) return;"
new_refresh = """if (!counts || counts.error) { if(window._dbg4_log) window._dbg4_log('API unread_counts: ERROR/null'); return; }
                            if(window._dbg4_log) window._dbg4_log('API unread_counts: recv=' + counts.unread_received + ' baby=' + counts.unread_baby + ' crs=' + counts.courses_pending_count + ' miss=' + counts.pending_missions_count);"""
if old_refresh in content:
    content = content.replace(old_refresh, new_refresh, 1)
    print('✅ Log ajouté dans refreshAllBadges')

# Ajouter des logs dans refreshMissionDots (après réception API)
old_mission = "if (!data || !data.rooms) return;"
new_mission = """if (!data || !data.rooms) { if(window._dbg4_log) window._dbg4_log('API rooms_missions: null/empty'); return; }
                            if(window._dbg4_log) window._dbg4_log('API rooms_missions: ' + JSON.stringify(data.rooms));"""
if old_mission in content:
    content = content.replace(old_mission, new_mission, 1)
    print('✅ Log ajouté dans refreshMissionDots')

# Ajouter un log APRÈS que les badges soient mis à jour par refreshAllBadges
old_badge_save = "// 5. Sauvegarde pour restauration rapide bfcache"
new_badge_save = """// 5. Log état DOM après update
                            if(window._dbg4_log) {
                                var _msgB = document.getElementById('bottomNavMessagesBadge');
                                var _crsB = document.getElementById('bottomNavCoursesBadge');
                                var _babyB = document.getElementById('room-baby-dot');
                                var _mDots = document.querySelectorAll('.room-mission-dot');
                                var _mVis = 0; _mDots.forEach(function(d){ if(d.style.display !== 'none') _mVis++; });
                                window._dbg4_log('DOM: msg=' + (_msgB?_msgB.style.display:'ABSENT') + ' crs=' + (_crsB?_crsB.style.display:'ABSENT') + ' baby=' + (_babyB?_babyB.style.display:'ABSENT') + ' missionVis=' + _mVis + '/' + _mDots.length);
                            }
                            // 5. Sauvegarde pour restauration rapide bfcache"""
if old_badge_save in content:
    content = content.replace(old_badge_save, new_badge_save, 1)
    print('✅ Log ajouté après update DOM badges')

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n🎯 Debug V4 prêt. Commit et push pour déployer.')
