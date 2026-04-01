#!/usr/bin/env python3
"""Diagnostic: vérifier l'état des badges courses pour tous les utilisateurs"""
import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# 1. player_reminders non cochés par maison
c.execute('SELECT house_id, COUNT(*) FROM player_reminders WHERE is_done=0 GROUP BY house_id')
print('=== player_reminders non cochés par maison ===')
for r in c.fetchall():
    print(f'  house_id={r[0]}: {r[1]} articles en attente')

# 2. Utilisateurs et maisons
c.execute('SELECT email, house_id, name FROM users ORDER BY house_id')
print('\n=== Utilisateurs ===')
for r in c.fetchall():
    print(f'  {r[2]} ({r[0]}) -> house_id={r[1]}')

# 3. courses_pending_count par maison
c.execute('SELECT DISTINCT house_id FROM users WHERE house_id IS NOT NULL')
houses = [r[0] for r in c.fetchall()]
for hid in houses:
    c.execute('SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0', (hid,))
    count = c.fetchone()[0] or 0
    print(f'\n  Maison {hid}: courses_pending_count = {count}')

# 4. Push subscriptions
try:
    c.execute('SELECT user_email, house_id FROM push_subscriptions')
    print('\n=== Push subscriptions ===')
    for r in c.fetchall():
        print(f'  {r[0]} -> house_id={r[1]}')
except Exception:
    print('\nPas de table push_subscriptions')

conn.close()
print('\n=== Diagnostic termine ===')
