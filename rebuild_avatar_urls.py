#!/usr/bin/env python3
"""
Reconstruire toutes les avatar_url avec le bon seed depuis la colonne avatar
"""
import sqlite3

DB = 'users.db'

def rebuild_all_urls():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Trouver tous les utilisateurs avec avatar (seed) et avatar_style
    c.execute("""
        SELECT email, avatar, avatar_style, avatar_url 
        FROM users 
        WHERE avatar IS NOT NULL 
        AND avatar != '' 
        AND avatar_style IS NOT NULL 
        AND avatar_style != ''
        AND avatar_url LIKE '%dicebear%'
    """)
    
    users = c.fetchall()
    fixed_count = 0
    
    for email, avatar, avatar_style, old_url in users:
        # Construire la nouvelle URL
        new_url = f'https://api.dicebear.com/7.x/{avatar_style}/svg?seed={avatar}'
        
        if old_url != new_url:
            print(f"✅ {email}: seed={avatar}, style={avatar_style}")
            print(f"   OLD: {old_url}")
            print(f"   NEW: {new_url}")
            
            # Mettre à jour
            c.execute("""
                UPDATE users 
                SET avatar_url = ? 
                WHERE email = ?
            """, (new_url, email))
            fixed_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ {fixed_count} URLs reconstruites")

if __name__ == '__main__':
    rebuild_all_urls()
