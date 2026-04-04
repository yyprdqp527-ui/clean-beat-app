import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('users.db')
c = conn.cursor()

c.execute('SELECT email, name, house_id FROM users WHERE house_id=173')
users = c.fetchall()
print('Users maison 173:')
for u in users:
    print('  email=%s name=%s house_id=%s' % u)

today = datetime.now().date()
week_start = (today - timedelta(days=today.weekday())).isoformat()
print('\nWeek start:', week_start)

results = []
for email, name, _ in users:
    c.execute('SELECT COALESCE(SUM(points), 0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at) >= ?', (email, week_start))
    wp = c.fetchone()[0]
    results.append((email, name, wp))
    print('  %s (%s): weekly=%d' % (name, email, wp))

results.sort(key=lambda x: x[2], reverse=True)
if results and results[0][2] > 0:
    print('\nWinner: %s (%s) with %d pts' % (results[0][1], results[0][0], results[0][2]))
    print('nnbn@lkj.com IS winner:', results[0][0] == 'nnbn@lkj.com')
else:
    print('\nNo winner (all 0 pts)')

conn.close()
