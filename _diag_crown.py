#!/usr/bin/env python3
"""Diagnostic: vérifier si la couronne fonctionne"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('users.db')
c = conn.cursor()

# 1. Trouver un house_id actif
c.execute('SELECT house_id, email, name FROM users WHERE house_id IS NOT NULL LIMIT 5')
users = c.fetchall()
print("=== Utilisateurs ===")
for u in users:
    print(f"  house={u[0]} | {u[2]} ({u[1]})")

if not users:
    print("AUCUN utilisateur!")
    exit()

hid = users[0][0]

# 2. Début de semaine
try:
    import pytz
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
except:
    now = datetime.now()

start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
print(f"\nstart_of_week = {start_of_week.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"now = {now.strftime('%Y-%m-%d %H:%M:%S')} (weekday={now.weekday()}, 6=dimanche)")

# 3. Weekly points
c.execute("""SELECT u.email, u.name, COALESCE(SUM(ct.points), 0) as weekly_pts
    FROM users u
    LEFT JOIN completed_tasks ct ON ct.user_email = u.email AND ct.house_id = u.house_id
        AND COALESCE(ct.completed_at, ct.date_done) >= ?
    WHERE u.house_id = ?
    GROUP BY u.email
    ORDER BY weekly_pts DESC
""", (start_of_week.strftime('%Y-%m-%d %H:%M:%S'), hid))
rows = c.fetchall()

print(f"\n=== weekly_points house_id={hid} ===")
for r in rows:
    print(f"  {r[1]} ({r[0]}): {r[2]} pts")

if rows and rows[0][2] > 0:
    print(f"\n>>> GAGNANT: {rows[0][1]} ({rows[0][0]}) avec {rows[0][2]} pts")
    print(f">>> La couronne devrait apparaitre sur cet avatar avec ?preview_sunday=1")
else:
    print(f"\n>>> AUCUN gagnant — tous a 0 points cette semaine!")
    print(f">>> C'est pour ca que la couronne ne s'affiche pas: weekly_points == 0")
    print(f">>> La condition exige weekly_points > 0 pour designer un gagnant")

conn.close()
