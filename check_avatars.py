#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour vérifier les avatars dans la base de données
"""

import sqlite3

DB = 'users.db'

conn = sqlite3.connect(DB)
c = conn.cursor()

print("=" * 80)
print("DIAGNOSTIC DES AVATARS")
print("=" * 80)

# Récupérer tous les utilisateurs avec leurs avatars
c.execute("""
    SELECT email, name, avatar, avatar_file, avatar_url, house_id
    FROM users
    WHERE house_id IS NOT NULL
    ORDER BY house_id, email
""")

users = c.fetchall()

if not users:
    print("\n❌ Aucun utilisateur trouvé dans une maison")
    conn.close()
    exit()

current_house = None
for email, name, avatar, avatar_file, avatar_url, house_id in users:
    if house_id != current_house:
        print(f"\n🏠 MAISON ID: {house_id}")
        print("-" * 80)
        current_house = house_id
    
    print(f"\n👤 {name or 'Sans nom'} ({email})")
    print(f"   📝 avatar        : {repr(avatar)}")
    print(f"   📁 avatar_file   : {repr(avatar_file)}")
    print(f"   🔗 avatar_url    : {repr(avatar_url)}")
    
    # Déterminer ce qui sera affiché
    if avatar_file and avatar_file != 'None':
        print(f"   ✅ AFFICHERA    : /static/avatars/{avatar_file}")
    elif avatar_url and avatar_url != 'None':
        print(f"   ✅ AFFICHERA    : {avatar_url}")
    elif avatar and len(str(avatar)) <= 4:
        print(f"   ✅ AFFICHERA    : Emoji {avatar}")
    else:
        print(f"   ⚠️  AFFICHERA    : Image par défaut (homme.png)")
        if avatar and avatar not in ['None', None]:
            print(f"   💡 SUGGESTION   : avatar contient '{avatar}' mais ne sera pas utilisé")
            print(f"                    Il faut peut-être migrer vers avatar_file ?")

conn.close()

print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)
print("""
Les avatars s'affichent dans cet ordre de priorité :
1. avatar_file (fichier uploadé dans /static/avatars/)
2. avatar_url (URL externe, ex: DiceBear)
3. avatar (emoji, max 4 caractères)
4. Image par défaut (homme.png)

Si vos avatars ne s'affichent pas, vérifiez que :
- Les fichiers existent dans /static/avatars/
- Les champs ne contiennent pas la chaîne "None"
- Les URLs sont valides
""")
