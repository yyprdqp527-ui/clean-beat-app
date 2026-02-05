#!/usr/bin/env python3
"""Script pour simuler la création d'un message baby_tracking comme le ferait l'API"""

import sqlite3
from datetime import datetime

def create_baby_message():
    # Paramètres du test (même que Lucien)
    house_id = 154
    player_email = 'child_154_1769583879@cleanbeat.internal'
    player_name = 'Lucien'
    task_name = 'Donner le biberon'
    tracking_time = '09:30'
    bottle_ml = '150' 
    observations = 'Test simulation - Bébé content'
    
    print("🧪 Simulation création message baby_tracking")
    print(f"👤 Joueur: {player_name} ({player_email})")
    print(f"🍼 Tâche: {task_name}")
    print(f"⏰ Heure: {tracking_time}")
    print(f"🥛 Quantité: {bottle_ml} ml")
    print(f"📝 Observations: {observations}")
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # 1. Insérer dans baby_tracking
    c.execute("""
        INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_email, house_id, 'biberon', tracking_time, bottle_ml, observations))
    
    print("✅ Entry baby_tracking créée")
    
    # 2. Créer le message pour la messagerie
    message_text = f"🍼 {player_name} a donné le biberon à {tracking_time} ({bottle_ml} ml)\n📝 {observations}"
    
    c.execute("""
        INSERT INTO messages (house_id, sender_email, sender_type, content, message_type)
        VALUES (?, ?, 'house', ?, 'baby_tracking')
    """, (house_id, player_email, message_text))
    
    message_id = c.lastrowid
    print(f"✅ Message créé avec ID: {message_id}")
    print(f"📨 Contenu: {message_text}")
    
    conn.commit()
    
    # 3. Vérifier que ça s'affiche dans la requête de comments
    c.execute("""
        SELECT m.id, m.sender_email, m.content, m.message_type,
               sender.name as sender_name, sender.avatar as sender_avatar
        FROM messages m
        LEFT JOIN users sender ON m.sender_email = sender.email
        WHERE m.id = ?
    """, (message_id,))
    
    row = c.fetchone()
    if row:
        print(f"🔍 Vérification jointure:")
        print(f"   sender_email: {row[1]}")
        print(f"   sender_name: {row[4]}")
        print(f"   sender_avatar: {row[5]}")
    
    conn.close()
    print("✅ Test terminé avec succès!")

if __name__ == '__main__':
    create_baby_message()