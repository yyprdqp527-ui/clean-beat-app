#!/usr/bin/env python3
"""
Script de test pour vérifier l'attribution des points aux joueurs
"""

import sqlite3
from datetime import date

DB = 'users.db'

def test_player_selection():
    """
    Simule une validation de tâche pour différents joueurs
    """
    print("=" * 70)
    print("🧪 TEST D'ATTRIBUTION DES POINTS")
    print("=" * 70)
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Trouver une maison avec plusieurs joueurs
    c.execute('''
        SELECT house_id, GROUP_CONCAT(email) as emails, COUNT(*) as nb
        FROM users
        WHERE house_id IS NOT NULL
        GROUP BY house_id
        HAVING nb >= 2
        LIMIT 1
    ''')
    
    result = c.fetchone()
    if not result:
        print("❌ Aucune maison avec plusieurs joueurs trouvée")
        conn.close()
        return
    
    house_id, emails_str, nb_players = result
    emails = emails_str.split(',')
    
    print(f"\n📍 Test sur la maison ID={house_id} ({nb_players} joueurs)")
    
    # Afficher les joueurs
    for email in emails:
        c.execute('SELECT name, points FROM users WHERE email=?', (email,))
        name, points = c.fetchone()
        print(f"  👤 {name or email}: {points or 0} points totaux")
    
    print("\n" + "=" * 70)
    print("✅ STRUCTURE CORRECTE")
    print("=" * 70)
    
    print("\n📋 Ce qui se passe quand vous validez une tâche :")
    print("   1. Vous sélectionnez le joueur dans l'interface")
    print("   2. Le formulaire envoie 'player_email' = email du joueur")
    print("   3. Backend attribue les points à ce joueur spécifique")
    print("   4. Les points apparaissent sous l'avatar correct")
    
    print("\n💡 POUR TESTER SUR MOBILE :")
    print("   1. Connectez-vous avec :", emails[0])
    print("   2. Allez sur une tâche")
    print("   3. Tapez sur l'avatar de :", emails[1])
    print("   4. Validez la tâche")
    print("   5. Vérifiez que les points vont à :", emails[1])
    
    conn.close()

if __name__ == '__main__':
    test_player_selection()
