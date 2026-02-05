#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT email, name, avatar, avatar_style, avatar_url FROM users WHERE email='fnfuieh@me.com'")
row = c.fetchone()
if row:
    email, name, avatar, style, url = row
    print(f"📧 Email: {email}")
    print(f"👤 Name: {name}")
    print(f"🎨 Avatar (seed): {avatar}")
    print(f"🎭 Style: {style}")
    print(f"🔗 URL: {url}")
else:
    print("❌ Utilisateur non trouvé")
conn.close()
