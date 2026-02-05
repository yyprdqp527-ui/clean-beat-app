#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de validation tâche bébé pour Marcel (house_id=150)
"""

import sqlite3
from datetime import datetime

conn = sqlite3.connect('menage.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 60)
print("🧪 CRÉATION MESSAGE BÉBÉ POUR MARCEL (house_id=150)")
print("=" * 60)

house_id = 150
user_email = "gfufgjdgdye@me.com"
task_name = "Donner le biberon"
tracking_time = "19:00"
bottle_ml = 180
observations = "Message test pour Marcel"

print(f"\n📦 Données:")
print(f"   - House: {house_id}")
print(f"   - User: {user_email}")
print(f"   - Time: {tracking_time}")
print(f"   - Quantity: {bottle_ml}ml")

# 1. Insérer dans baby_tracking
cursor.execute("""
    INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (user_email, house_id, task_name, tracking_time, bottle_ml, observations, datetime.now()))
conn.commit()
print("\n✅ baby_tracking créé")

# 2. Créer le message
content = f"🍼 {tracking_time} - Biberon donné ({bottle_ml}ml)\n📝 {observations}"

cursor.execute("""
    INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, timestamp, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (house_id, 'system', 'house', content, 'baby_tracking', datetime.now(), datetime.now()))
conn.commit()
message_id = cursor.lastrowid
print(f"✅ Message créé avec ID: {message_id}")

# 3. Vérifier
cursor.execute("""
    SELECT id, message_type, substr(content,1,60) 
    FROM messages 
    WHERE house_id = ? 
    ORDER BY id DESC 
    LIMIT 5
""", (house_id,))
messages = cursor.fetchall()

print(f"\n📬 Messages dans la maison {house_id}:")
for msg in messages:
    print(f"   - ID {msg['id']}: [{msg['message_type']}] {msg[2]}")

conn.close()

print("\n" + "=" * 60)
print("✅ TERMINÉ")
print("=" * 60)
print("\n🔍 Allez sur http://localhost:8000/comments")
print("   Vous devriez voir le message ROSE !")
