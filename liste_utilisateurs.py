import sqlite3

DB = "users.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("Utilisateurs inscrits :")
for row in c.execute("SELECT id, email, name FROM users"):
    print(row)

conn.close()
