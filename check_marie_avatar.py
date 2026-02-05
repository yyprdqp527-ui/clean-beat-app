#!/usr/bin/env python3
import sqlite3

DB = 'users.db'
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("SELECT name, avatar, avatar_style, avatar_url, avatar_file FROM users WHERE email='fnfuieh@me.com';")
result = c.fetchone()
conn.close()

if result:
    print(f"Nom: {result[0]}")
    print(f"Avatar (seed): {result[1]}")
    print(f"Avatar Style: {result[2]}")
    print(f"Avatar URL: {result[3]}")
    print(f"Avatar File: {result[4]}")
else:
    print("Utilisateur non trouvé")
