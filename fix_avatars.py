#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour corriger les avatars mal stockés dans la base de données.
Migre les URLs et numéros du champ 'avatar' vers les champs appropriés.
"""

import sqlite3

DB = 'users.db'

# Liste des avatars par ID (utilisés avant)
AVATAR_URLS = [
    'https://avatar.iran.liara.run/public/1',
    'https://avatar.iran.liara.run/public/2', 
    'https://avatar.iran.liara.run/public/3',
    'https://avatar.iran.liara.run/public/4',
    'https://avatar.iran.liara.run/public/5',
    'https://avatar.iran.liara.run/public/6',
    'https://avatar.iran.liara.run/public/7',
    'https://avatar.iran.liara.run/public/8',
    'https://avatar.iran.liara.run/public/9',
    'https://avatar.iran.liara.run/public/10',
    'https://avatar.iran.liara.run/public/11',
    'https://avatar.iran.liara.run/public/12'
]

def get_avatar_url(avatar_id):
    """Retourne l'URL de l'avatar basé sur l'ID"""
    try:
        idx = int(avatar_id)
        if 0 <= idx < len(AVATAR_URLS):
            return AVATAR_URLS[idx]
        return AVATAR_URLS[0]
    except (ValueError, IndexError):
        return AVATAR_URLS[0]

def fix_avatars():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    print("=" * 80)
    print("CORRECTION DES AVATARS")
    print("=" * 80)
    
    # 1. Migrer les URLs du champ avatar vers avatar_url
    c.execute("""
        SELECT email, name, avatar, avatar_url
        FROM users
        WHERE avatar LIKE 'http%' AND (avatar_url IS NULL OR avatar_url = '')
    """)
    urls_to_migrate = c.fetchall()
    
    if urls_to_migrate:
        print(f"\n🔄 Migration de {len(urls_to_migrate)} URL(s) vers avatar_url:")
        for email, name, avatar, avatar_url in urls_to_migrate:
            print(f"  ✅ {name} ({email}): {avatar[:50]}...")
            c.execute("""
                UPDATE users 
                SET avatar_url = ?, avatar = NULL
                WHERE email = ?
            """, (avatar, email))
        conn.commit()
        print(f"  → {len(urls_to_migrate)} utilisateur(s) corrigé(s)")
    
    # 2. Convertir les numéros (IDs) en URLs
    c.execute("""
        SELECT email, name, avatar, avatar_url, avatar_file
        FROM users
        WHERE avatar GLOB '[0-9]*' 
          AND avatar NOT LIKE '%http%'
          AND (avatar_url IS NULL OR avatar_url = '')
          AND (avatar_file IS NULL OR avatar_file = '' OR avatar_file = 'homme.png')
    """)
    numbers_to_convert = c.fetchall()
    
    if numbers_to_convert:
        print(f"\n🔄 Conversion de {len(numbers_to_convert)} ID(s) d'avatar en URLs:")
        for email, name, avatar, avatar_url, avatar_file in numbers_to_convert:
            new_url = get_avatar_url(avatar)
            print(f"  ✅ {name} ({email}): ID '{avatar}' → {new_url}")
            c.execute("""
                UPDATE users 
                SET avatar_url = ?, avatar = NULL, avatar_file = NULL
                WHERE email = ?
            """, (new_url, email))
        conn.commit()
        print(f"  → {len(numbers_to_convert)} utilisateur(s) corrigé(s)")
    
    # 3. Nettoyer les avatar_file = homme.png quand il y a un meilleur avatar
    c.execute("""
        SELECT email, name, avatar, avatar_url, avatar_file
        FROM users
        WHERE avatar_file = 'homme.png' 
          AND avatar_url IS NOT NULL 
          AND avatar_url != ''
          AND avatar_url != 'None'
    """)
    homme_to_clean = c.fetchall()
    
    if homme_to_clean:
        print(f"\n🔄 Nettoyage de {len(homme_to_clean)} avatar_file='homme.png' redondants:")
        for email, name, avatar, avatar_url, avatar_file in homme_to_clean:
            print(f"  ✅ {name} ({email}): suppression de homme.png (a déjà avatar_url)")
            c.execute("""
                UPDATE users 
                SET avatar_file = NULL
                WHERE email = ?
            """, (email,))
        conn.commit()
        print(f"  → {len(homme_to_clean)} utilisateur(s) nettoyé(s)")
    
    # 4. Rapport final
    print("\n" + "=" * 80)
    print("RAPPORT FINAL")
    print("=" * 80)
    
    c.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN avatar_file IS NOT NULL AND avatar_file != '' AND avatar_file != 'None' THEN 1 ELSE 0 END) as with_file,
            SUM(CASE WHEN avatar_url IS NOT NULL AND avatar_url != '' AND avatar_url != 'None' THEN 1 ELSE 0 END) as with_url,
            SUM(CASE WHEN avatar IS NOT NULL AND avatar != '' AND LENGTH(avatar) <= 4 THEN 1 ELSE 0 END) as with_emoji
        FROM users
        WHERE house_id IS NOT NULL
    """)
    stats = c.fetchone()
    
    print(f"\n📊 Statistiques des avatars (utilisateurs avec maison):")
    print(f"   Total: {stats[0]}")
    print(f"   Avec fichier (avatar_file): {stats[1]}")
    print(f"   Avec URL (avatar_url): {stats[2]}")
    print(f"   Avec emoji (avatar): {stats[3]}")
    
    conn.close()
    print("\n✅ Correction des avatars terminée!")

if __name__ == '__main__':
    fix_avatars()
