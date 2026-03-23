#!/usr/bin/env python3
"""Test d'affichage des badges suspicion sur les avatars"""
import sqlite3
from datetime import date

def test_suspicion_badges():
    house_id = 150
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Récupérer suspicions
    suspicion_map = {}
    c.execute("""
        SELECT suspected_player_email, COUNT(*)
        FROM suspicions
        WHERE house_id=? AND status IN ('pending', 'awaiting_validation')
        GROUP BY suspected_player_email
    """, (house_id,))
    for row in c.fetchall():
        suspicion_map[row[0]] = int(row[1])
    
    # Récupérer les joueurs
    c.execute("SELECT email, name FROM users WHERE house_id=? ORDER BY email", (house_id,))
    
    print("=== TEST BADGES SUSPICION ===\n")
    for row in c.fetchall():
        email, name = row
        suspicion_count = suspicion_map.get(email, 0)
        suspicion_active = suspicion_count > 0
        
        print(f"👤 {name} ({email[:30]})")
        print(f"   suspicion_count = {suspicion_count}")
        print(f"   suspicion_active = {suspicion_active}")
        
        # Simuler le template Jinja2
        if suspicion_active:
            print(f"   ✅ HTML devrait contenir: <span class=\"avatar-emoji-badge\" title=\"Suspicion active\" style=\"right: auto; left: -6px;\">🔍</span>")
        else:
            print(f"   ❌ Pas de badge loupe")
        print()
    
    conn.close()

if __name__ == '__main__':
    test_suspicion_badges()
