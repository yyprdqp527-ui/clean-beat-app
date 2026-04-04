import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('users.db')
c = conn.cursor()

today = datetime.now().date()
week_start = (today - timedelta(days=today.weekday())).isoformat()
print(f'Semaine depuis: {week_start}')
print()

c.execute('SELECT DISTINCT house_id FROM users WHERE house_id IS NOT NULL ORDER BY house_id')
houses = [r[0] for r in c.fetchall()]

for hid in houses:
    c.execute('SELECT email, name FROM users WHERE house_id=?', (hid,))
    members = c.fetchall()
    has_points = False
    rows = []
    for email, name in members:
        c.execute('SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at) >= ?', (email, week_start))
        wp = c.fetchone()[0]
        rows.append((email, name, wp))
        if wp > 0:
            has_points = True
    if has_points:
        print(f'=== House {hid} ===')
        for email, name, wp in rows:
            print(f'  {name} ({email}): {wp} pts')
        print()

conn.close()
