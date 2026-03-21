#!/usr/bin/env python3
"""
Migration : Marquer tous les enfants existants avec is_child_account = 1
Les enfants ont un email du type child_*@cleanbeat.internal
"""
import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Trouver tous les enfants (email commençant par child_ et finissant par @cleanbeat.internal)
c.execute("""
    SELECT email, name 
    FROM users 
    WHERE email LIKE 'child_%@cleanbeat.internal'
    AND (is_child_account IS NULL OR is_child_account = 0)
""")

children = c.fetchall()
print(f"🔍 {len(children)} enfant(s) trouvé(s) à corriger:")
for email, name in children:
    print(f"   - {name} ({email})")

if children:
    # Mettre à jour is_child_account = 1 pour tous les enfants
    c.execute("""
        UPDATE users 
        SET is_child_account = 1 
        WHERE email LIKE 'child_%@cleanbeat.internal'
    """)
    
    conn.commit()
    print(f"\n✅ {len(children)} enfant(s) mis à jour avec is_child_account = 1")
else:
    print("\n✅ Aucun enfant à corriger")

conn.close()
print("\n✅ Migration terminée !")
