#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inject gameplay button HTML and CSS into menu.html
"""

import shutil

# Backup
shutil.copy('templates/menu.html', 'templates/menu.html.backup_gameplay')

# CSS to inject
css_code = """        /* Bouton Gameplay à droite du header */
        .gameplay-btn-wrapper {
            display: flex !important;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            z-index: 999999 !important;
            position: fixed !important;
            right: 14px !important;
            top: 14px !important;
            flex-shrink: 0;
            pointer-events: auto !important;
            visibility: visible !important;
            opacity: 1 !important;
            background: rgba(255,0,255,0.3) !important;
            padding: 10px !important;
        }
        .gameplay-btn {
            width: 70px !important;
            height: 70px !important;
            background: cyan !important;
            border: 5px solid blue !important;
            border-radius: 50%;
            display: flex !important;
            align-items: center;
            justify-content: center;
            font-size: 32px !important;
            cursor: pointer !important;
            text-decoration: none !important;
            pointer-events: auto !important;
            z-index: 99999 !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        .gameplay-label {
            font-size: 12px !important;
            font-weight: 700 !important;
            color: black !important;
            background: yellow !important;
            padding: 2px 4px !important;
        }
"""

# HTML to inject
html_code = """                <div class="gameplay-btn-wrapper">
                    <a href="{{ url_for('gameplay') }}" class="gameplay-btn" title="Gameplay">🎮</a>
                    <div class="gameplay-label">Jeu</div>
                </div>
"""

# Read file
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find insertion point for CSS (after .burger-wrapper or around line 382)
css_marker = '.burger-wrapper {'
if css_marker in content:
    # Insert CSS after burger-wrapper CSS block ends
    idx = content.find(css_marker)
    # Find the closing } of burger-wrapper
    idx_end = content.find('}', idx) + 1
    new_content = content[:idx_end] + '\n' + css_code + content[idx_end:]
else:
    print("⚠️ .burger-wrapper not found, using line-based insertion")
    lines = content.split('\n')
    lines.insert(382, css_code)
    new_content = '\n'.join(lines)

# Find insertion point for HTML (inside header-menu)
html_marker = '<div class="header-menu">'
if html_marker in new_content:
    idx = new_content.find(html_marker)
    # Find the end of this line
    idx_end = new_content.find('\n', idx) + 1
    final_content = new_content[:idx_end] + html_code + new_content[idx_end:]
else:
    print("⚠️ header-menu not found in expected format")
    final_content = new_content

# Write back
with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(final_content)

print('✅ CSS et HTML du bouton gameplay injectés')
print(f'✅ Backup sauvé dans templates/menu.html.backup_gameplay')
