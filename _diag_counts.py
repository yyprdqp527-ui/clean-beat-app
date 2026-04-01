import sqlite3
from datetime import date, timedelta

conn = sqlite3.connect('users.db')
c = conn.cursor()

today = date.today().isoformat()
monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
first_month = date.today().replace(day=1).isoformat()

print(f"Aujourd'hui: {today}")
print(f"Lundi: {monday}")
print(f"1er du mois: {first_month}")

c.execute("SELECT COUNT(*) FROM completed_tasks WHERE DATE(completed_at) = ?", (today,))
print(f"Jour (completed_at): {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM completed_tasks WHERE DATE(date_done) = ?", (today,))
print(f"Jour (date_done): {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM completed_tasks WHERE DATE(COALESCE(completed_at, date_done)) = ?", (today,))
print(f"Jour (COALESCE): {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM completed_tasks WHERE DATE(COALESCE(completed_at, date_done)) >= ?", (monday,))
print(f"Semaine (COALESCE): {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM completed_tasks WHERE DATE(COALESCE(completed_at, date_done)) >= ?", (first_month,))
print(f"Mois (COALESCE): {c.fetchone()[0]}")

# Dernières tâches
c.execute("SELECT completed_at, date_done FROM completed_tasks ORDER BY ROWID DESC LIMIT 8")
print("\nDernières tâches:")
for r in c.fetchall():
    print(f"  completed_at={r[0]}, date_done={r[1]}")

conn.close()
