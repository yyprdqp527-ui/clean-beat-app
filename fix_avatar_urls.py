#!/usr/bin/env python3
"""Script pour corriger les URLs d'avatars qui ne correspondent pas aux seeds"""

import sqlite3
import re

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Trouver tous les utilisateurs avec un seed et une URL qui ne correspondent pas
c.execute("SELECT email, name, avatar, avatar_url FROM users WHERE avatar != '' AND avatar_url LIKE '%seed=%'")
users = c.fetchall()

mismatches = []
for email, name, avatar, avatar_url in users:
    if not avatar_url:
        continue
    # Extraire le seed de l'URL
    match = re.search(r'seed=([^&]+)', avatar_url)
    if match:
        url_seed = match.group(1)
        if avatar != url_seed:
            mismatches.append((email, name, avatar, url_seed, avatar_url))
            print(f"⚠️  {name} ({email}): avatar={avatar} mais URL seed={url_seed}")

if mismatches:
    print(f"\n❌ Trouvé {len(mismatches)} incohérences")
    
    # Corriger automatiquement
    for email, name, avatar, url_seed, avatar_url in mismatches:
        # Extraire le style de l'URL
        style_match = re.search(r'/7\.x/([^/]+)/', avatar_url)
        style = style_match.group(1) if style_match else 'lorelei'
        new_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={avatar}"
        c.execute("UPDATE users SET avatar_url=? WHERE email=?", (new_url, email))
        print(f"✅ Corrigé {email}: seed={avatar}, style={style}")
    
    conn.commit()
    print(f"\n🎉 {len(mismatches)} URLs corrigées")
else:
    print("✅ Aucune incohérence trouvée")

conn.close()
