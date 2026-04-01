#!/usr/bin/env python3
"""Replace debug banner V1 with V3 (DOM diagnostic)."""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_start = '<!-- \U0001f527 DEBUG TEMPORAIRE'
old_end_marker = '</script>\n\n<script>'

start_idx = content.find(old_start)
assert start_idx != -1, "Start marker not found"

end_of_script = content.find(old_end_marker, start_idx)
assert end_of_script != -1, "End marker not found"
end_idx = end_of_script + len('</script>\n')

new_block = """<!-- \U0001f527 DEBUG V3 — diagnostic DOM complet -->
<div id="_dbg_banner" style="position:fixed;top:0;left:0;right:0;background:#FFD700;color:#000;z-index:99999;padding:8px 10px;font-size:11px;font-weight:bold;text-align:left;font-family:monospace;border-bottom:2px solid #000;max-height:40vh;overflow-y:auto;">
    SSR: MSG={{ unread_messages_count|default('NULL') }} BABY={{ unread_baby_tracking|default('NULL') }} COURSES={{ courses_pending_count|default('NULL') }} MISSIONS={{ rooms_with_new_missions|length }}<br>
    <span id="_dbg_dom">DOM: chargement...</span>
    <button onclick="this.parentElement.style.display='none'" style="position:absolute;top:2px;right:6px;cursor:pointer;font-size:16px;">\u2715</button>
</div>
<script>
(function() {
    function diag() {
        var lines = [];
        var msgB = document.getElementById('bottomNavMessagesBadge');
        lines.push('MSG badge: ' + (msgB ? 'display=' + getComputedStyle(msgB).display + ' text=' + msgB.textContent.trim() + ' class=' + msgB.className : 'ABSENT'));
        var crsB = document.getElementById('bottomNavCoursesBadge');
        lines.push('CRS badge: ' + (crsB ? 'display=' + getComputedStyle(crsB).display + ' text=' + crsB.textContent.trim() + ' class=' + crsB.className : 'ABSENT'));
        var babyD = document.getElementById('room-baby-dot');
        lines.push('BABY dot: ' + (babyD ? 'display=' + getComputedStyle(babyD).display + ' text=' + babyD.textContent.trim() + ' w=' + babyD.offsetWidth + 'x' + babyD.offsetHeight : 'ABSENT'));
        var mDots = document.querySelectorAll('.room-mission-dot');
        var visCount = 0;
        mDots.forEach(function(d) { if (getComputedStyle(d).display !== 'none') visCount++; });
        lines.push('MISSION dots: ' + mDots.length + ' total, ' + visCount + ' visibles');
        if (mDots.length > 0) {
            var d0 = mDots[0];
            lines.push('dot[0]: display=' + getComputedStyle(d0).display + ' w=' + d0.offsetWidth + 'x' + d0.offsetHeight + ' text=' + d0.textContent.trim());
            var p = d0.parentElement;
            lines.push('dot[0].parent: overflow=' + getComputedStyle(p).overflow + ' pos=' + getComputedStyle(p).position + ' w=' + p.offsetWidth + 'x' + p.offsetHeight);
        }
        var cwWrap = document.getElementById('cwWrap');
        lines.push('cwWrap: ' + (cwWrap ? 'EXISTE' : 'ABSENT'));
        var cards = document.querySelectorAll('.room-card-visual[data-category]');
        lines.push('Room cards: ' + cards.length);
        var el = document.getElementById('_dbg_dom');
        if (el) el.innerHTML = lines.join('<br>');
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() { setTimeout(diag, 2000); });
    } else {
        setTimeout(diag, 2000);
    }
})();
</script>
"""

content = content[:start_idx] + new_block + content[end_idx:]

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Done. Replaced {end_idx - start_idx} chars with {len(new_block)} chars")
