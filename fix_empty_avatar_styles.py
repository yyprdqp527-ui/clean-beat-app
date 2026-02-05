#!/usr/bin/env python3
"""
Script pour remplir les avatar_style vides en extrayant le style depuis avatar_url
"""
import sqlite3
import re

DB = 'users.db'

def fix_empty_styles():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Trouver tous les utilisateurs avec avatar_url mais avatar_style vide
    c.execute("""
        SELECT email, avatar, avatar_url, avatar_style 
        FROM users 
        WHERE avatar_url IS NOT NULL 
        AND avatar_url != '' 
        AND (avatar_style IS NULL OR avatar_style = '')
    """)
    
    users = c.fetchall()
    fixed_count = 0
    
    for email, avatar, avatar_url, avatar_style in users:
        # Extraire le style de l'URL
        match = re.search(r'dicebear\.com/[^/]+/([^/]+)/', avatar_url)
        if match:
            extracted_style = match.group(1)
            print(f"✅ {email}: style='{avatar_style}' → '{extracted_style}'")
            
            # Mettre à jour
            c.execute("""
                UPDATE users 
                SET avatar_style = ? 
                WHERE email = ?
            """, (extracted_style, email))
            fixed_count += 1
        else:
            print(f"⚠️  {email}: Impossible d'extraire le style de {avatar_url}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ {fixed_count} utilisateurs corrigés")

if __name__ == '__main__':
    fix_empty_styles()
