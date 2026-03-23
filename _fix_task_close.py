#!/usr/bin/env python3
"""
1. Corriger la fermeture manquante du div gw-task-item dans le JS
2. Vérifier la syntaxe Jinja2
"""

with open('templates/gameplay.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Fermeture manquante du gw-task-item
old_close = "                         + actBtns\n                         + '</div>';\n                }).join('');"
new_close = "                         + actBtns\n                         + '</div>'\n                         + '</div>';\n                }).join('');"

if old_close in c:
    c = c.replace(old_close, new_close, 1)
    print("✅ Fermeture div gw-task-item corrigée")
else:
    print("⚠️  Fermeture déjà correcte ou pattern différent")
    # Cherche le pattern
    idx = c.find("+ actBtns")
    if idx != -1:
        print(f"  Contexte actBtns: {repr(c[idx:idx+100])}")

# Vérifier la syntaxe de base (nb de { et } Jinja2 équilibrés)
jinja_opens = c.count('{%')
jinja_closes = c.count('%}')
print(f"\nJinja2 : {jinja_opens} ouvertures, {jinja_closes} fermetures")

script_opens = c.count('<script')
script_closes = c.count('</script>')
print(f"Script : {script_opens} ouvertures, {script_closes} fermetures")

with open('templates/gameplay.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("\n✅ Fichier sauvegardé")
