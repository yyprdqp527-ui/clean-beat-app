#!/usr/bin/env python3
"""Diagnostic complet couronne"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Quel user est connecté? Regarder les sessions Flask
# Trouver TOUS les house_id avec des joueurs
c.execute('SELECT DISTINCT house_id FROM users WHERE house_id IS NOT NULL ORDER BY house_id')
house_ids = [r[0] for r in c.fetchall()]
print(f"House IDs: {house_ids}")

try:
    import pytz
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
except:
    now = datetime.now()

week_start = (now.date() - timedelta(days=now.date().weekday())).isoformat()
print(f"week_start (DATE format) = {week_start}")
print(f"now = {now}")

for hid in house_ids:
    c.execute('SELECT email, name FROM users WHERE house_id=?', (hid,))
    users = c.fetchall()
    if not users:
        continue
    
    print(f"\n{'='*50}")
    print(f"HOUSE {hid}: {[u[1] for u in users]}")
    
    for email, name in users:
        # Exactement comme get_players_for_house
        c.execute("""
            SELECT COALESCE(SUM(points), 0), COUNT(*) 
            FROM completed_tasks 
            WHERE user_email=? AND DATE(completed_at) >= ?
        """, (email, week_start))
        weekly = c.fetchone()
        weekly_points = int(weekly[0]) if weekly[0] else 0
        weekly_tasks = int(weekly[1]) if weekly[1] else 0
        print(f"  {name} ({email}): weekly_points={weekly_points}, tasks={weekly_tasks}")
        
        # Dernières taches
        c.execute("""
            SELECT task_name, points, completed_at 
            FROM completed_tasks 
            WHERE user_email=? 
            ORDER BY completed_at DESC LIMIT 3
        """, (email,))
        for t in c.fetchall():
            print(f"    -> {t[0]}: {t[1]}pts @ {t[2]}")

conn.close()
