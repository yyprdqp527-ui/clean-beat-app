#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacer le CSS .beta-dot par ORANGE ÉNORME
old_beta_dot = """.beta-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #fff;
    border: 1.5px solid rgba(255,255,255,0.4);
    cursor: pointer;
    animation: beta-blink 2s ease-in-out infinite;
    flex-shrink: 0;
}"""

new_beta_dot = """.beta-dot {
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
    font-weight: bold;
}"""

if old_beta_dot in content:
    content = content.replace(old_beta_dot, new_beta_dot)
    
    with open('templates/menu.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ .beta-dot transformé en GROS bouton ORANGE 70px!")
    print("🔴 Avec symbole hamburger ☰ noir au centre")
else:
    print("❌ .beta-dot CSS non trouvé - vérifions...")
    # Chercher une version similaire
    if "width: 10px; height: 10px" in content and "beta-dot" in content:
        print("⚠️  CSS trouvé mais format différent - modification manuelle nécessaire")
    else:
        print("❌ .beta-dot introuvable dans le fichier")
