import sqlite3

DB = "users.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("Maisons existantes :")
for row in c.execute("SELECT id, code, name, house_name FROM houses"):
    print(row)

conn.close()
