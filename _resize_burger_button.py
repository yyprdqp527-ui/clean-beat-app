#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Réduire le bouton beta-dot à une taille normale et style élégant
old_beta_css = """.beta-dot {
    width: 70px !important;
    height: 70px !important;
    border-radius: 50%;
    background: orange !important;
    border: 6px solid red !important;
    cursor: pointer;
    flex-shrink: 0;
    z-index: 999999 !important;
    box-shadow: 0 0 30px rgba(255, 69, 0, 0.8) !important;
    animation: none !important;
    position: relative;
}
.beta-dot::before {
    content: '☰';
    font-size: 32px;
    color: black;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-weight: bold; pointer-events: none;
}"""

new_beta_css = """.beta-dot {
    width: 46px;
    height: 46px;
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(166,211,220,0.25) 100%);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 2px solid rgba(255,255,255,0.5);
    cursor: pointer;
    flex-shrink: 0;
    z-index: 2001;
    box-shadow: 0 8px 24px rgba(89,113,118,0.2), inset 0 1px 0 rgba(255,255,255,0.6);
    animation: none;
    position: relative;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
}
.beta-dot::before {
    content: '☰';
    font-size: 22px;
    color: #153036;
    font-weight: bold;
    pointer-events: none;
    line-height: 1;
}
.beta-dot:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 32px rgba(89,113,118,0.3), inset 0 1px 0 rgba(255,255,255,0.7);
    border-color: rgba(253,174,84,0.6);
}
.beta-dot:active {
    transform: translateY(0) scale(0.95);
}"""

if old_beta_css in content:
    content = content.replace(old_beta_css, new_beta_css)
    print("✅ CSS beta-dot remplacé par style élégant 46px")
else:
    print("⚠️  CSS beta-dot non trouvé exact, recherche partielle...")
    # Chercher juste le bloc .beta-dot {
    import re
    pattern = r'\.beta-dot\s*\{[^}]+\}'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    if matches:
        print(f"   Trouvé {len(matches)} blocs .beta-dot")

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("🎨 Bouton burger maintenant élégant et discret (46px)")
