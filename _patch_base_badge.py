import io

SCRIPT = (
    '\n<!-- Badge icone accueil : recalcule a chaque chargement de page -->\n'
    '<script>\n'
    '(function() {\n'
    '    if (!(\'setAppBadge\' in navigator)) return;\n'
    '    fetch(\'/api/unread_counts\', { cache: \'no-store\', credentials: \'same-origin\' })\n'
    '        .then(function(r) { return r.ok ? r.json() : null; })\n'
    '        .then(function(counts) {\n'
    '            if (!counts) return;\n'
    '            var total = (counts.unread_received || 0)\n'
    '                      + (counts.unread_task_added || 0)\n'
    '                      + (counts.unread_courses_added || 0)\n'
    '                      + (counts.unread_baby || 0);\n'
    '            if (total > 0) {\n'
    '                navigator.setAppBadge(total).catch(function(){});\n'
    '            } else {\n'
    '                navigator.clearAppBadge().catch(function(){});\n'
    '            }\n'
    '        })\n'
    '        .catch(function() {});\n'
    '})();\n'
    '</script>\n'
)

with io.open('templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

TARGET = '</body>'
MARKER = 'Badge icone accueil : recalcule a chaque'

if MARKER in content:
    print('Script already present — nothing to do')
elif TARGET in content:
    content = content.replace(TARGET, SCRIPT + TARGET, 1)
    with io.open('templates/base.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Script inserted OK — base.html updated')
else:
    print('ERROR: </body> not found in base.html')
