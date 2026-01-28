#!/usr/bin/env python3
"""Script de vérification complète du système d'avatars"""

import sqlite3
import os

DB = "/Users/anne-gaelledaval/Downloads/Appli web-2/users.db"
AVATARS_DIR = "/Users/anne-gaelledaval/Downloads/Appli web-2/static/avatars"

print("🔍 Vérification complète du système d'avatars\n")

# 1. Vérifier les fichiers SVG
print("1️⃣ Fichiers d'avatars disponibles:")
svg_files = [f for f in os.listdir(AVATARS_DIR) if f.endswith('.svg')]
png_files = [f for f in os.listdir(AVATARS_DIR) if f.endswith('.png')]
print(f"   • {len(svg_files)} fichiers SVG")
print(f"   • {len(png_files)} fichiers PNG")
print()

# 2. Vérifier le profil de Doris
print("2️⃣ Profil actuel de Doris:")
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("SELECT name, avatar, avatar_file, avatar_url FROM users WHERE email='agdaval@yahoo.fr'")
row = c.fetchone()
if row:
    name, avatar, avatar_file, avatar_url = row
    print(f"   • Nom: {name}")
    print(f"   • avatar (emoji): {repr(avatar)}")
    print(f"   • avatar_file: {repr(avatar_file)}")
    print(f"   • avatar_url: {repr(avatar_url)}")
    
    if avatar_file:
        file_path = os.path.join(AVATARS_DIR, avatar_file)
        exists = os.path.exists(file_path)
        print(f"   • Fichier existe: {'✅' if exists else '❌'}")
print()

# 3. Test de mise à jour
print("3️⃣ Simulation de sélection d'avatar:")
test_avatar = "avatar_girl_3.svg"
print(f"   • Avatar sélectionné: {test_avatar}")

c.execute("""
    UPDATE users 
    SET avatar_file=?, avatar=NULL, avatar_url=NULL 
    WHERE email='agdaval@yahoo.fr'
""", (test_avatar,))
conn.commit()

c.execute("SELECT avatar_file FROM users WHERE email='agdaval@yahoo.fr'")
new_file = c.fetchone()[0]
print(f"   • Enregistré en base: {repr(new_file)}")
print(f"   • {'✅ OK' if new_file == test_avatar else '❌ ERREUR'}")

conn.close()
print()

print("📝 Actions à faire:")
print("   1. Rechargez edit_player avec Cmd+Shift+R")
print("   2. Cliquez sur un avatar de la banque")
print("   3. Vérifiez dans la console (F12) que vous voyez:")
print("      📤 Données envoyées:")
print("        email: agdaval@yahoo.fr")
print("        name: Doris")
print("        avatar: [nom du fichier]")
print("        avatar_type: file")
print("   4. Cliquez sur Enregistrer")
print("   5. Rechargez le menu avec Cmd+Shift+R")
