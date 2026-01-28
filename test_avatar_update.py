#!/usr/bin/env python3
"""
Script de test pour vérifier la mise à jour des avatars
"""
import sqlite3

DB = "users.db"

# Simuler une mise à jour d'avatar DiceBear
test_email = "pat@hotmail.com"
test_seed = "lorelei3"
test_style = "lorelei"
test_avatar_url = f"https://api.dicebear.com/7.x/{test_style}/svg?seed={test_seed}"

print("🧪 TEST DE MISE À JOUR D'AVATAR")
print("=" * 60)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Avant
print(f"\n📊 AVANT la mise à jour :")
c.execute("SELECT name, avatar, avatar_file, avatar_url FROM users WHERE email=?", (test_email,))
row = c.fetchone()
if row:
    print(f"   Nom: {row[0]}")
    print(f"   avatar: {row[1]}")
    print(f"   avatar_file: {row[2]}")
    print(f"   avatar_url: {row[3]}")

# Mise à jour (simuler ce que fait update_player)
print(f"\n🔄 Mise à jour avec :")
print(f"   seed: {test_seed}")
print(f"   style: {test_style}")
print(f"   avatar_url: {test_avatar_url}")

c.execute("""
    UPDATE users 
    SET avatar_url=?, avatar=NULL, avatar_file=NULL 
    WHERE email=?
""", (test_avatar_url, test_email))
conn.commit()

# Après
print(f"\n📊 APRÈS la mise à jour :")
c.execute("SELECT name, avatar, avatar_file, avatar_url FROM users WHERE email=?", (test_email,))
row = c.fetchone()
if row:
    print(f"   Nom: {row[0]}")
    print(f"   avatar: {row[1]}")
    print(f"   avatar_file: {row[2]}")
    print(f"   avatar_url: {row[3]}")

conn.close()

print("\n✅ Test terminé")
print("\n💡 Vérifie maintenant dans l'application si l'avatar de 'pat' affiche bien lorelei3")
