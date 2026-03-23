#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplifier le bouton gameplay avec style élégant et animation pulse
"""

import shutil

# Backup
shutil.copy('templates/menu.html', 'templates/menu.html.backup_simplify')

# Lire le fichier
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# CSS debug à remplacer
old_css = """          /* Bouton Gameplay à droite du header */
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
          .gameplay-btn:hover {
            transform: translateY(-2px);
          }
          .gameplay-btn:active {
            transform: scale(0.95);
          }
          .gameplay-label {
            font-size: 12px !important;
            font-weight: 700 !important;
            color: black !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: center;
            background: yellow !important;
            padding: 2px 4px !important;
          }"""

# Nouveau CSS élégant avec animation
new_css = """          /* Bouton Gameplay avec animation pulse */
          @keyframes pulse-gameplay {
              0%, 100% { transform: scale(1); }
              50% { transform: scale(1.1); }
          }
          
          .gameplay-btn-wrapper {
            position: fixed;
            right: 14px;
            top: 14px;
            z-index: 9999;
            pointer-events: auto;
          }
          
          .gameplay-btn {
            width: 50px;
            height: 50px;
            background: rgba(255, 255, 255, 0.24);
            backdrop-filter: saturate(180%) blur(30px);
            -webkit-backdrop-filter: saturate(180%) blur(30px);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            cursor: pointer;
            text-decoration: none;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.55);
            transition: transform 0.2s ease;
            animation: pulse-gameplay 2s ease-in-out infinite;
          }
          
          .gameplay-btn:hover {
            animation: none;
            transform: scale(1.05);
          }
          
          .gameplay-btn:active {
            transform: scale(0.95);
          }"""

# HTML ancien
old_html = """                <div class="gameplay-btn-wrapper">
                    <a href="{{ url_for('gameplay') }}" class="gameplay-btn" title="Gameplay">🎮</a>
                    <div class="gameplay-label">Jeu</div>
                </div>"""

# Nouveau HTML sans label
new_html = """                <div class="gameplay-btn-wrapper">
                    <a href="{{ url_for('gameplay') }}" class="gameplay-btn" title="Gameplay">🎮</a>
                </div>"""

# Remplacer
if old_css in content:
    content = content.replace(old_css, new_css)
    print('✅ CSS remplacé')
else:
    print('⚠️ Ancien CSS non trouvé')

if old_html in content:
    content = content.replace(old_html, new_html)
    print('✅ HTML simplifié (label retiré)')
else:
    print('⚠️ Ancien HTML non trouvé')

# Écrire
with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Bouton gameplay simplifié avec animation pulse')
