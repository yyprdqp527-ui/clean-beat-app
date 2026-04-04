import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Simuler le calcul de players pour house 173 (le compte nnbn@lkj.com)
week_start = (datetime.now().date() - timedelta(days=datetime.now().date().weekday())).isoformat()

c.execute('SELECT email, name FROM users WHERE house_id=173')
members = c.fetchall()

players = []
for email, name in members:
    c.execute('SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at) >= ?', (email, week_start))
    wp = c.fetchone()[0]
    players.append({'email': email, 'name': name, 'weekly_points': wp})

print("Players:", players)

# Calcul du gagnant (meme logique que app.py)
_sorted = sorted(players, key=lambda x: x.get('weekly_points', 0), reverse=True)
print("Sorted:", _sorted)

if _sorted and _sorted[0].get('weekly_points', 0) > 0:
    winner_name = _sorted[0].get('name', '')
    winner_email = _sorted[0].get('email', '')
    print(f"Winner: {winner_name} ({winner_email})")
else:
    print("NO WINNER (all 0 pts)")

# Verifier aussi si current_user_name == nnbn@lkj.com match le gagnant
current_user = 'nnbn@lkj.com'
print(f"\ncurrent_user_name = '{current_user}'")
print(f"winner_email = '{winner_email}'")
print(f"is_sunday check: winner_email == current_user_name ? {winner_email == current_user}")

# Le winner est Isabelle - verifier others
others = [p for p in players if p['email'] != current_user]
print(f"\nothers = {others}")
if others:
    p2 = others[0]
    print(f"p2.email = '{p2['email']}'")
    print(f"winner_email == p2.email ? {winner_email == p2['email']}")

conn.close()
