#!/usr/bin/env python3
"""
Script de test pour le système de messages de la maison
"""

import sqlite3

DB = 'users.db'

def test_house_messages():
    """Test le système de messages de la maison"""
    
    print("🏠 Test du système de messages de la maison")
    print("-" * 50)
    
    # Connexion à la base
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Trouver une maison de test (maison 149 - Biscotte)
    house_id = 149
    
    # Vérifier que la maison existe
    c.execute("SELECT id, name, house_name FROM houses WHERE id=?", (house_id,))
    house = c.fetchone()
    
    if not house:
        print("❌ Maison 149 introuvable")
        conn.close()
        return
    
    house_name = house[2] if house[2] else house[1]
    print(f"✅ Maison trouvée: {house_name} (ID: {house_id})")
    
    # Compter les joueurs
    c.execute("SELECT COUNT(*) FROM users WHERE house_id=?", (house_id,))
    player_count = c.fetchone()[0]
    print(f"👥 Nombre de joueurs: {player_count}")
    
    # Vérifier les messages existants de la maison
    c.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE house_id=? AND sender_type='house'
    """, (house_id,))
    house_message_count = c.fetchone()[0]
    print(f"💬 Messages de la maison existants: {house_message_count}")
    
    # Afficher les derniers messages de la maison
    print("\n📜 Derniers messages de la maison:")
    c.execute("""
        SELECT sender_email, content, message_type, timestamp
        FROM messages 
        WHERE house_id=? AND sender_type='house'
        ORDER BY timestamp DESC
        LIMIT 5
    """, (house_id,))
    
    messages = c.fetchall()
    if messages:
        for msg in messages:
            sender_name, content, msg_type, timestamp = msg
            print(f"  [{msg_type}] {sender_name}: {content}")
            print(f"      → {timestamp}")
    else:
        print("  Aucun message de la maison pour le moment")
    
    # Vérifier l'activité récente (si la table tasks existe)
    try:
        from datetime import datetime, timedelta
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        
        c.execute("""
            SELECT COUNT(*) FROM tasks 
            WHERE house_id=? AND completed=1 AND completed_at > ?
        """, (house_id, three_days_ago))
        recent_tasks = c.fetchone()[0]
        
        print(f"\n📊 Activité récente (3 derniers jours):")
        print(f"  Tâches complétées: {recent_tasks}")
        
        if recent_tasks == 0:
            print("  ⚠️ Aucune activité → La maison devrait envoyer un sermon !")
        elif recent_tasks > 10:
            print("  🎉 Beaucoup d'activité → La maison devrait féliciter !")
        else:
            print("  ✅ Activité normale")
    except sqlite3.OperationalError:
        print("\n⚠️ Table 'tasks' non trouvée - skip vérification activité")
    
    conn.close()
    print("\n✅ Test terminé")

if __name__ == "__main__":
    test_house_messages()
