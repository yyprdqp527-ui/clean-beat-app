#!/usr/bin/env python3
"""
Script pour tester manuellement le système de suivi bébé
Simule une validation de tâche avec suivi
"""

import sqlite3
from datetime import datetime

DB = "menage.db"

def simulate_baby_tracking():
    """Simule une entrée de suivi bébé"""
    print("\n🍼 SIMULATION DE SUIVI BÉBÉ")
    print("="*60)
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Trouver un utilisateur et une maison
    c.execute("SELECT email, name, house_id FROM users WHERE house_id IS NOT NULL LIMIT 1")
    user = c.fetchone()
    
    if not user:
        print("❌ Aucun utilisateur trouvé avec une maison")
        conn.close()
        return
    
    user_email, user_name, house_id = user
    print(f"\n👤 Utilisateur: {user_name} ({user_email})")
    print(f"🏠 Maison ID: {house_id}")
    
    # Créer une entrée de suivi
    tracking_time = "14:30"
    bottle_ml = 180
    observations = "Test: bébé a bien bu 🍼"
    task_type = "biberon"
    
    print(f"\n📝 Création d'une entrée de suivi:")
    print(f"   Type: {task_type}")
    print(f"   Heure: {tracking_time}")
    print(f"   Quantité: {bottle_ml} ml")
    print(f"   Observations: {observations}")
    
    # Insérer dans baby_tracking
    c.execute("""
        INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_email, house_id, task_type, tracking_time, bottle_ml, observations))
    
    tracking_id = c.lastrowid
    print(f"✅ Entrée créée (ID: {tracking_id})")
    
    # Créer le message pour la messagerie
    message_text = f"🍼 {user_name} a donné le biberon à {tracking_time} ({bottle_ml} ml)\n📝 {observations}"
    
    print(f"\n💬 Création du message:")
    print(f"   {message_text}")
    
    # Récupérer le nom de la maison
    c.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
    house_row = c.fetchone()
    sender_name = house_row[0] if house_row and house_row[0] else (house_row[1] if house_row else "Maison")
    
    # Insérer dans messages
    c.execute("""
        INSERT INTO messages (house_id, sender_email, sender_type, content, message_type)
        VALUES (?, ?, 'house', ?, 'baby_tracking')
    """, (house_id, sender_name, message_text))
    
    message_id = c.lastrowid
    print(f"✅ Message créé (ID: {message_id})")
    
    conn.commit()
    
    # Vérifier
    print(f"\n🔍 Vérification:")
    
    c.execute("SELECT COUNT(*) FROM baby_tracking WHERE house_id=?", (house_id,))
    count = c.fetchone()[0]
    print(f"   Entrées baby_tracking pour cette maison: {count}")
    
    c.execute("SELECT COUNT(*) FROM messages WHERE house_id=? AND message_type='baby_tracking'", (house_id,))
    count = c.fetchone()[0]
    print(f"   Messages baby_tracking pour cette maison: {count}")
    
    # Afficher le dernier message
    c.execute("""
        SELECT id, sender_email, content, timestamp, created_at
        FROM messages
        WHERE house_id=? AND message_type='baby_tracking'
        ORDER BY id DESC
        LIMIT 1
    """, (house_id,))
    
    msg = c.fetchone()
    if msg:
        msg_id, sender, content, timestamp, created = msg
        print(f"\n📨 Dernier message de suivi bébé:")
        print(f"   ID: {msg_id}")
        print(f"   De: {sender}")
        print(f"   Contenu: {content}")
        print(f"   Créé: {created or timestamp}")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ SIMULATION TERMINÉE")
    print("="*60)
    print("\n💡 Vous pouvez maintenant aller dans la messagerie (/comments)")
    print("   pour voir le message de suivi bébé")

if __name__ == "__main__":
    simulate_baby_tracking()
