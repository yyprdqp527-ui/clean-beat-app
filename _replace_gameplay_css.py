#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remplacer le CSS gameplay debug par un style élégant avec regex
"""

import re
import shutil

# Backup
shutil.copy('templates/menu.html', 'templates/menu.html.backup_regex')

# Lire
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Nouveau CSS élégant
new_css = """        /* Bouton Gameplay avec animation pulse */
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

# Créer un pattern regex flexible pour matcher tout le bloc CSS gameplay (avec n'importe quelle indentation)
# De "/* Bouton Gameplay" jusqu'à la fermeture de .gameplay-label ou .gameplay-btn:active
pattern = r'/\*\s*Bouton Gameplay.*?\.gameplay-(btn:active|label)\s*\{[^}]*\}'

# Trouver tous les blocs CSS gameplay et les remplacer
matches = list(re.finditer(pattern, content, re.DOTALL))
print(f'Trouvé {len(matches)} bloc(s) CSS gameplay')

# Remplacer par le nouveau CSS (en gardant seulement une occurrence)
if matches:
    # Supprimer tous les blocs
    for match in reversed(matches):  # Reverse pour ne pas décaler les index
        content = content[:match.start()] + content[match.end():]
    
    # Insérer le nouveau CSS à la place du premier
    insert_pos = matches[0].start()
    content = content[:insert_pos] + new_css + content[insert_pos:]
    print('✅ CSS remplacé par le nouveau style avec animation pulse')
else:
    print('⚠️ Aucun bloc CSS gameplay trouvé')
    # Fallback: insérer après .burger-wrapper
    if '.burger-wrapper {' in content:
        idx = content.find('.burger-wrapper {')
        # Trouver la fin du bloc burger-wrapper
        idx_end = content.find('}', idx) + 1
        content = content[:idx_end] + '\n\n' + new_css + content[idx_end:]
        print('✅ CSS inséré après .burger-wrapper')

# Écrire
with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Modifications terminées')
