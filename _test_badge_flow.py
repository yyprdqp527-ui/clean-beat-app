#!/usr/bin/env python3
"""Test de bout en bout: vérifier les données badge pour 2 joueurs"""
import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Maison 168 (8 courses en attente)
c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=168 AND is_done=0")
pending = c.fetchone()[0]
print(f"MAISON 168: {pending} courses non cochees")

c.execute("SELECT email, name FROM users WHERE house_id=168")
users168 = c.fetchall()
print(f"Joueurs: {users168}")

for email, name in users168:
    c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=168 AND is_done=0")
    courses = c.fetchone()[0]
    print(f"  {name}: courses_pending = {courses}")

# Verifier que le WebSocket broadcasting marche: les rooms SocketIO
# On peut pas tester ca sans le serveur, mais verifions les push_subscriptions
try:
    c.execute("SELECT user_email, house_id FROM push_subscriptions")
    subs = c.fetchall()
    print(f"\nPush subscriptions: {len(subs)}")
    for s in subs:
        print(f"  {s[0]} -> house_id={s[1]}")
except:
    print("\nPas de table push_subscriptions")

# Verifier qu'il n'y a pas de CSS display:none !important qui cache le badge
import re
with open('templates/menu.html', 'r') as f:
    html = f.read()

# Chercher tout CSS qui cible bottomNavCoursesBadge ou bottom-nav-badge avec display:none !important
matches = re.findall(r'(?:bottom-nav-badge|bottomNavCoursesBadge)[^}]*display\s*:\s*none\s*!important', html)
print(f"\nCSS display:none !important sur badges: {len(matches)} match(es)")
for m in matches:
    print(f"  TROUVÉ: ...{m[:80]}...")

# Chercher si display:none !important dans le CSS general
all_important_none = re.findall(r'[^}]*display\s*:\s*none\s*!important[^}]*', html)
print(f"\nTous les display:none !important: {len(all_important_none)}")
for m in all_important_none:
    clean = m.strip()[:120]
    print(f"  {clean}")

conn.close()
