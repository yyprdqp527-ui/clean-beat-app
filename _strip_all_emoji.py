#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supprime TOUS les émojis des console.log pour éviter les erreurs de parsing JavaScript dans Safari
"""
import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern pour trouver les emoji communs dans les console.log
emoji_pattern = r'[👤✅🔴🍔⚡🚀💡📱🎨🔥⭐🎯🏆📊💫🌟🎭🎉📧🎁🔔🔊]+'

# Fonction pour nettoyer une ligne de console.log
def clean_console_log(match):
    line = match.group(0)
    # Supprimer les émojis
    cleaned = re.sub(emoji_pattern + r'\s*', '', line)
    return cleaned

# Remplacer dans tous les console.log
content = re.sub(
    r"console\.(log|error|warn|info)\([^)]*\)",
    clean_console_log,
    content
)

# Sauvegarder
with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Tous les émojis supprimés des console.log/error/warn/info")
print("🔄 Redémarrez Flask et videz le cache Safari")
