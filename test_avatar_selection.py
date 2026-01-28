#!/usr/bin/env python3
"""Script pour tester la sélection d'avatar"""

import sqlite3
import sys

DB = "/Users/anne-gaelledaval/Downloads/Appli web-2/users.db"

def test_avatar_update(email, avatar_filename):
    """Simule la mise à jour d'avatar comme le fait update_player()"""
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # État avant
    c.execute("SELECT name, avatar, avatar_file, avatar_url FROM users WHERE email=?", (email,))
    row = c.fetchone()
    if not row:
        print(f"❌ Utilisateur {email} non trouvé")
        return
    
    name, old_avatar, old_avatar_file, old_avatar_url = row
    print(f"👤 {name} ({email})")
    print(f"   Avant: avatar_file={repr(old_avatar_file)}")
    
    # Mise à jour (comme le fait avatar_type='file')
    c.execute("""
        UPDATE users 
        SET avatar_file=?, avatar=NULL, avatar_url=NULL 
        WHERE email=?
    """, (avatar_filename, email))
    conn.commit()
    
    # État après
    c.execute("SELECT avatar, avatar_file, avatar_url FROM users WHERE email=?", (email,))
    new_avatar, new_avatar_file, new_avatar_url = c.fetchone()
    
    print(f"   Après: avatar_file={repr(new_avatar_file)}")
    print(f"   ✅ Avatar mis à jour vers: {avatar_filename}")
    
    conn.close()

if __name__ == "__main__":
    # Test avec Doris
    print("🧪 Test de mise à jour d'avatar\n")
    
    email = "agdaval@yahoo.fr"
    avatar = "avatar_girl_1.svg"
    
    test_avatar_update(email, avatar)
    
    print("\n📝 Maintenant:")
    print("   1. Rechargez la page menu (Cmd+Shift+R)")
    print("   2. L'avatar devrait être visible")
