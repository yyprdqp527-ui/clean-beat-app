import sqlite3
from datetime import date, timedelta

conn = sqlite3.connect('users.db')
c = conn.cursor()
today = date(2026, 4, 4)
ws = (today - timedelta(days=today.weekday())).isoformat()
print('Week start:', ws)

for hid in [150, 173]:
    c.execute('SELECT email FROM users WHERE house_id=?', (hid,))
    emails = [r[0] for r in c.fetchall()]
    c.execute('SELECT user_email, COALESCE(SUM(points),0) FROM completed_tasks WHERE house_id=? AND DATE(completed_at) >= ? GROUP BY user_email', (hid, ws))
    wmap = dict(c.fetchall())
    players = [{'email': e, 'wp': wmap.get(e, 0)} for e in emails]
    players.sort(key=lambda x: x['wp'], reverse=True)
    winner = players[0] if players and players[0]['wp'] > 0 else None
    print(f'\nHouse {hid}: {players}')
    print(f'  Winner: {winner}')

conn.close()
