import sqlite3

DB = "users.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("Liste des maisons :")
for row in c.execute("SELECT id, house_name, name FROM houses"):
    print(row)

conn.close()
