#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supprime tous les émojis des commentaires et strings JavaScript pour éviter les erreurs de parsing
"""
import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

output = []
in_script = False
emoji_pattern = r'[👤✅🔴🍔⚡🚀💡📱🎨🔥⭐🎯🏆📊💫🌟🎁🔔🔊🎭🎉📧🌈💝🏠✨]'

for line in lines:
    # Détecter si on est dans un bloc <script>
    if '<script>' in line or '<script ' in line:
        in_script = True
    if '</script>' in line:
        in_script = False
    
    # Si on est dans un script, supprimer les émojis des commentaires //
    if in_script and '//' in line:
        # Supprimer émojis seulement dans la partie commentaire
        parts = line.split('//', 1)
        if len(parts) == 2:
            # Nettoyer le commentaire
            cleaned_comment = re.sub(emoji_pattern, '', parts[1])
            line = parts[0] + '//' + cleaned_comment
    
    output.append(line)

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.writelines(output)

print("✅ Émojis supprimés des commentaires JavaScript")
print("🔄 Redémarrez Flask")
