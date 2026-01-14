import sqlite3

DB = "users.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("Utilisateurs et leur maison :")
for row in c.execute("SELECT email, house_id FROM users"):
    print(row)

print("\nMaisons :")
for row in c.execute("SELECT id, name, house_name, code FROM houses"):
    print(row)

conn.close()
