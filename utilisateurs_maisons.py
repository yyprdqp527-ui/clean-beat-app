import sqlite3

DB = "users.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("Utilisateurs et leur maison associée :")
for row in c.execute("""
    SELECT users.email, users.name, users.house_id, houses.name, houses.house_name
    FROM users LEFT JOIN houses ON users.house_id = houses.id
"""):
    print(row)

conn.close()
