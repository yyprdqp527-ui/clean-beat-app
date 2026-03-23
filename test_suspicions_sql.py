import sqlite3

# Connexion DB
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Simuler l'utilisateur Emma
email = 'child_emma_1767776538@cleanbeat.local'

print(f"Test pour {email}:\n")

# Suspicions contre Emma
c.execute("""
    SELECT s.id, s.suspecting_player_email, u.name, s.task_name, 
           s.task_points, s.status, s.photo_path, s.created_at
    FROM suspicions s
    JOIN users u ON u.email = s.suspecting_player_email
    WHERE s.suspected_player_email=?
    ORDER BY s.created_at DESC
    LIMIT 20
""", (email,))
against = c.fetchall()

print(f"Suspicions CONTRE {email}: {len(against)}")
for row in against:
    print(f"  - ID {row[0]}: {row[2]} ({row[1]}) | {row[3]} | status={row[5]}")

# Suspicions PAR Emma
c.execute("""
    SELECT s.id, s.suspected_player_email, u.name, s.task_name, 
           s.task_points, s.status, s.photo_path, s.created_at
    FROM suspicions s
    JOIN users u ON u.email = s.suspected_player_email
    WHERE s.suspecting_player_email=?
    ORDER BY s.created_at DESC
    LIMIT 20
""", (email,))
by_me = c.fetchall()

print(f"\nSuspicions PAR {email}: {len(by_me)}")
for row in by_me:
    print(f"  - ID {row[0]}: contre {row[2]} ({row[1]}) | {row[3]} | status={row[5]}")

conn.close()
