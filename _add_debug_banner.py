#!/usr/bin/env python3
"""Ajoute un bandeau de diagnostic temporaire sur le menu pour identifier le problème."""

FILE = 'templates/menu.html'

with open(FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trouver la ligne <body>
body_idx = None
for i, l in enumerate(lines):
    if '<body>' in l:
        body_idx = i
        break

if body_idx is None:
    print('ERREUR: <body> non trouvé')
    exit(1)

# Insérer le bandeau APRÈS <body>
debug_banner = '''<!-- 🔧 DEBUG TEMPORAIRE — supprimer après diagnostic -->
<div id="_dbg_banner" style="position:fixed;top:0;left:0;right:0;background:#FFD700;color:#000;z-index:99999;padding:6px 10px;font-size:12px;font-weight:bold;text-align:center;font-family:monospace;border-bottom:2px solid #000;">
    SSR: MSG={{ unread_messages_count|default('NULL') }} | BABY={{ unread_baby_tracking|default('NULL') }} | COURSES={{ courses_pending_count|default('NULL') }} | MISSIONS={{ rooms_with_new_missions|length }} |
    <span id="_dbg_js">JS: en attente...</span>
    <button onclick="this.parentElement.style.display='none'" style="margin-left:10px;cursor:pointer;">✕</button>
</div>
<script>
// Mettre à jour le bandeau avec les valeurs JS après fetch API
(function() {
    setTimeout(function() {
        fetch('/api/unread_counts', { cache: 'no-store', credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(c) {
                var el = document.getElementById('_dbg_js');
                if (el) el.textContent = 'API: MSG=' + (c.unread_received||0) + ' BABY=' + (c.unread_baby||0) + ' COURSES=' + (c.courses_pending_count||0) + ' MISSIONS=' + (c.pending_missions_count||0);
            })
            .catch(function(e) {
                var el = document.getElementById('_dbg_js');
                if (el) el.textContent = 'API ERREUR: ' + e;
            });
    }, 1000);
})();
</script>
'''

lines.insert(body_idx + 1, debug_banner)

with open(FILE, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'✅ Bandeau debug inséré après <body> (ligne {body_idx+1})')
print(f'   Lignes: {len(lines)}')
