#!/usr/bin/env python3
"""
Script de test pour simuler la validation d'une tâche bébé et vérifier 
que les messages apparaissent bien dans la messagerie.
"""

import sqlite3
from datetime import datetime
import sys
import os

# Ajouter le répertoire parent au path pour pouvoir importer app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def simulate_baby_task_validation():
    """Simule la validation d'une tâche bébé et vérifie les messages"""
    
    print("🍼 Test de validation tâche bébé - Biberon")
    print("=" * 50)
    
    # Paramètres de test
    house_id = 154
    player_email = 'ag@me.com'
    player_name = 'Anne-gaëlle'
    task_name = 'Donner le biberon'
    tracking_time = datetime.now().strftime('%H:%M')
    bottle_ml = '150'
    observations = 'Test intégration messagerie'
    
    # Connexion à la base
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # 1. Sauvegarder dans baby_tracking
    print(f"📝 1. Sauvegarde dans baby_tracking...")
    c.execute("""
        INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_email, house_id, 'biberon', tracking_time, bottle_ml, observations))
    
    tracking_id = c.lastrowid
    print(f"   ✅ ID tracking: {tracking_id}")
    
    # 2. Créer le message pour la messagerie
    print(f"📨 2. Création du message baby_tracking...")
    message_text = f"🍼 {player_name} a donné le biberon à {tracking_time} ({bottle_ml} ml)"
    if observations:
        message_text += f"\n📝 {observations}"
    
    c.execute("""
        INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (house_id, player_email, 'house', message_text, 'baby_tracking', datetime.now().isoformat()))
    
    message_id = c.lastrowid
    print(f"   ✅ ID message: {message_id}")
    print(f"   📄 Contenu: {message_text}")
    
    conn.commit()
    
    # 3. Vérifier que le message est récupéré par la requête /comments
    print(f"🔍 3. Test requête /comments...")
    c.execute("""
        SELECT m.id, m.sender_email, m.recipient_email, m.content, m.timestamp, m.sender_type, m.message_type,
               sender.name, sender.avatar
        FROM messages m
        LEFT JOIN users sender ON m.sender_email = sender.email
        WHERE m.house_id = ? 
        AND (
            (m.message_type = 'private' AND (m.sender_email = ? OR m.recipient_email = ?))
            OR (m.sender_type = 'house' AND m.message_type NOT IN ('task_completed'))
        )
        AND m.id = ?
    """, (house_id, player_email, player_email, message_id))
    
    result = c.fetchone()
    if result:
        msg_id, sender_email, recipient_email, content, timestamp, sender_type, message_type, sender_name, sender_avatar = result
        print(f"   ✅ Message trouvé dans /comments!")
        print(f"      ID: {msg_id}")
        print(f"      Sender: {sender_email} ({sender_name})")
        print(f"      Type: {sender_type} / {message_type}")
        print(f"      Content: {content}")
    else:
        print(f"   ❌ Message NON trouvé dans /comments!")
        return False
    
    # 4. Compter tous les messages baby_tracking pour cette maison
    print(f"📊 4. Statistiques messages baby_tracking...")
    c.execute("""
        SELECT COUNT(*) 
        FROM messages 
        WHERE house_id = ? AND message_type = 'baby_tracking'
    """, (house_id,))
    
    count = c.fetchone()[0]
    print(f"   📈 Total messages baby_tracking: {count}")
    
    # 5. Lister les 5 derniers messages baby_tracking
    print(f"📋 5. Derniers messages baby_tracking:")
    c.execute("""
        SELECT m.id, m.sender_email, m.content, m.timestamp, sender.name
        FROM messages m
        LEFT JOIN users sender ON m.sender_email = sender.email
        WHERE m.house_id = ? AND m.message_type = 'baby_tracking'
        ORDER BY m.timestamp DESC
        LIMIT 5
    """, (house_id,))
    
    recent_messages = c.fetchall()
    for i, msg in enumerate(recent_messages, 1):
        msg_id, sender_email, content, timestamp, sender_name = msg
        print(f"   {i}. ID {msg_id} - {sender_name or sender_email}")
        print(f"      {content}")
        print(f"      {timestamp}")
        print()
    
    conn.close()
    
    print("✅ Test terminé avec succès!")
    print("\n🌐 Pour voir les messages, connectez-vous sur:")
    print("   http://192.168.1.149:8000/comments")
    
    return True

if __name__ == "__main__":
    simulate_baby_task_validation()