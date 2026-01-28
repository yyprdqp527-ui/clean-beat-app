import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

c.execute("SELECT email, name, avatar, avatar_file, avatar_url FROM users WHERE house_id IS NOT NULL LIMIT 5")
for row in c.fetchall():
    print(f"\nEmail: {row[0]}")
    print(f"  Name: {row[1]}")
    print(f"  avatar: {repr(row[2])}")
    print(f"  avatar_file: {repr(row[3])}")
    print(f"  avatar_url: {repr(row[4])}")

conn.close()
