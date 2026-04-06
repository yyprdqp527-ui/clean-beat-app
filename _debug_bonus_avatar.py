import sqlite3, re

conn = sqlite3.connect('users.db')
c = conn.cursor()

player_email = 'child_150_1775380975@cleanbeat.internal'
house_id = 150

# Precharger avatars
_house_avatars = {}
c.execute('SELECT name, avatar, avatar_file, avatar_url FROM users WHERE house_id=?', (house_id,))
for _ua in c.fetchall():
    if _ua[0]:
        _house_avatars[_ua[0]] = {'avatar': _ua[1], 'avatar_file': _ua[2], 'avatar_url': _ua[3]}

print("=== house_avatars ===")
for k, v in _house_avatars.items():
    print(f"  {k}: {v}")

# Bonus/malus
c.execute("""SELECT ct.task_name, ct.category, ct.points, ct.completed_at
    FROM completed_tasks ct
    WHERE ct.user_email=? AND ct.category IN ('bonus','malus')
    AND ct.completed_at >= datetime('now', '-48 hours')
    ORDER BY ct.completed_at DESC LIMIT 20""", (player_email,))
rows = c.fetchall()
print(f"\n=== {len(rows)} bonus/malus rows for {player_email} ===")
for r in rows:
    raw = r[0] or ''
    m = re.match(r'^(?:[^\w]*?)(?:Bonus|Malus)\s+de\s+(.+?)\s*:\s*(.+)$', raw)
    giver = m.group(1).strip() if m else ''
    reason = m.group(2).strip() if m else ''
    print(f"  raw={raw!r}")
    print(f"  -> giver={giver!r}, reason={reason!r}")
    if giver and giver in _house_avatars:
        print(f"  -> avatar: {_house_avatars[giver]}")
    else:
        print(f"  -> NO AVATAR for {giver!r}")

# Aussi: tester la fenetre 48h
c.execute("SELECT datetime('now'), datetime('now', '-48 hours')")
r = c.fetchone()
print(f"\n=== Fenetre temps ===")
print(f"  now={r[0]}, 48h_ago={r[1]}")

# Tester sans filtre 48h
c.execute("""SELECT ct.task_name, ct.category, ct.points, ct.completed_at
    FROM completed_tasks ct
    WHERE ct.user_email=? AND ct.category IN ('bonus','malus')
    ORDER BY ct.completed_at DESC LIMIT 20""", (player_email,))
rows2 = c.fetchall()
print(f"\n=== SANS filtre 48h: {len(rows2)} rows ===")
for r in rows2:
    print(f"  {r}")

conn.close()
