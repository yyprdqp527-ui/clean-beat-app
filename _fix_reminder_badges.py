#!/usr/bin/env python3
"""Fix 4: Ajoute refreshAllBadges() dans les handlers reminder_added et reminder_toggle."""

import re

filepath = 'templates/menu.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# On cherche le pattern exact des deux handlers et on insère la ligne avant });
# Pattern: socket.on('reminder_added' / 'reminder_toggle', function(data) { ... });
# On utilise une regex pour trouver les blocs

def add_refresh_badge(handler_name, text):
    global changes
    # Pattern: fermeture   }  \n  (espaces)  });  après avoir trouvé le handler
    # On cherche: socket.on('handler_name', function(data) { ... });
    pattern = r"(socket\.on\('" + re.escape(handler_name) + r"'[^}]+})\s*\n(\s*\}\s*\n(\s*\}\s*\n)?\s*\}\s*\n\s*\});"
    # Approche plus simple : chercher le texte exact avec une modification ciblée
    marker = "socket.on('" + handler_name + "', function(data) {"
    idx = text.find(marker)
    if idx == -1:
        print(f"  HANDLER {handler_name} NON TROUVÉ")
        return text
    
    # Trouver le });  qui ferme ce handler
    # Après l'ouverture, chercher le premier });  (avec espaces devant)
    search_from = idx + len(marker)
    close_marker = "\n                        });"
    close_idx = text.find(close_marker, search_from)
    if close_idx == -1:
        # Essai avec moins d'espaces
        close_marker = "\n                    });"
        close_idx = text.find(close_marker, search_from)
    if close_idx == -1:
        print(f"  FERMETURE de {handler_name} NON TROUVÉE")
        return text
    
    # Vérifier qu'il n'y a pas déjà refreshAllBadges entre idx et close_idx
    block = text[idx:close_idx]
    if 'refreshAllBadges' in block:
        print(f"  {handler_name}: refreshAllBadges déjà présent, skip")
        return text
    
    # Récupérer l'indentation de });
    indent_line = close_marker  # ex: "\n                        });"
    # Insérer la ligne de refresh juste avant });
    indent = ""
    for ch in close_marker[1:]:  # skip \n
        if ch == ' ':
            indent += ch
        else:
            break
    
    insert_line = f"\n{indent}if (window.refreshAllBadges) window.refreshAllBadges();"
    new_text = text[:close_idx] + insert_line + text[close_idx:]
    print(f"  {handler_name}: OK (inséré à pos {close_idx})")
    changes += 1
    return new_text

content = add_refresh_badge('reminder_added', content)
content = add_refresh_badge('reminder_toggle', content)

if changes > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n{changes} modification(s) appliquée(s) dans {filepath}")
else:
    print("\nAucune modification appliquée")
