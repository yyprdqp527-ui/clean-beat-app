#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valide la syntaxe JavaScript du script burger en utilisant Node.js
"""
import subprocess
import tempfile
import os

# Extraire le script burger depuis le HTML servi
html = subprocess.check_output(['curl', '-s', 'http://127.0.0.1:8000/menu'], 
                               encoding='utf-8', timeout=5)

# Trouver le début du script burger
start_marker = "// 🍔 MENU BURGER - Définition globale immédiate"
start = html.find(start_marker)
if start == -1:
    print("❌ Script burger non trouvé dans le HTML")
    exit(1)

# Trouver la fermeture du script (</script>)
end = html.find("</script>", start)
if end == -1:
    print("❌ Fermeture du script non trouvée")
    exit(1)

# Extraire le JavaScript
js_code = html[start:end]

print("📄 Script burger extrait:")
print("=" * 60)
print(js_code)
print("=" * 60)
print()

# Créer un fichier temporaire et vérifier avec Node.js
with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
    f.write(js_code)
    temp_file = f.name

try:
    # Essayer de parser avec Node.js
    result = subprocess.run(
        ['node', '--check', temp_file],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Syntaxe JavaScript valide!")
    else:
        print("❌ Erreur de syntaxe JavaScript:")
        print(result.stderr)
finally:
    os.unlink(temp_file)
