#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test direct de validation de tâche bébé
Simule exactement ce que fait le endpoint /api/validate_task
"""

import sqlite3
import json
from datetime import datetime

# Connexion à la base de données
conn = sqlite3.connect('menage.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 60)
print("🧪 TEST VALIDATION DIRECTE TÂCHE BÉBÉ")
print("=" * 60)

# Données de test
user_email = "ag@me.com"
house_id = 154
task_name = "Donner le biberon"
category = "chambre_bebe"
tracking_time = "18:30"
bottle_ml = 150
observations = "Test de validation directe"

print(f"\n📦 Données de test:")
print(f"   - User: {user_email}")
print(f"   - House: {house_id}")
print(f"   - Task: {task_name}")
print(f"   - Category: {category}")
print(f"   - Time: {tracking_time}")
print(f"   - Quantity: {bottle_ml}ml")
print(f"   - Obs: {observations}")

# 1. Insérer dans baby_tracking
print("\n1️⃣ Insertion dans baby_tracking...")
cursor.execute("""
    INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (user_email, house_id, task_name, tracking_time, bottle_ml, observations, datetime.now()))
conn.commit()
print("   ✅ Données baby_tracking insérées")

# 2. Créer le message système
print("\n2️⃣ Création du message système...")

# Construire le contenu du message
if "biberon" in task_name.lower():
    content = f"🍼 {tracking_time} - Biberon donné ({bottle_ml}ml)"
elif "couche" in task_name.lower():
    content = f"🧷 {tracking_time} - Couche changée"
else:
    content = f"😴 {tracking_time} - Bébé mis au lit"

if observations:
    content += f"\n📝 {observations}"

print(f"   📝 Contenu: {content}")

# Insérer le message
cursor.execute("""
    INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, timestamp, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (house_id, 'system', 'house', content, 'baby_tracking', datetime.now(), datetime.now()))
conn.commit()
message_id = cursor.lastrowid
print(f"   ✅ Message créé avec ID: {message_id}")

# 3. Vérifier que le message existe
print("\n3️⃣ Vérification des messages...")
cursor.execute("SELECT * FROM messages WHERE house_id = ? ORDER BY id DESC LIMIT 5", (house_id,))
messages = cursor.fetchall()

print(f"   📨 Nombre total de messages: {len(messages)}")
for msg in messages:
    print(f"   - ID {msg['id']}: {msg['message_type']} | {msg['content'][:50]}...")

# 4. Vérifier la requête SQL utilisée dans /comments
print("\n4️⃣ Test requête SQL de /comments...")
cursor.execute("""
    SELECT * FROM messages 
    WHERE house_id = ? 
    AND message_type NOT IN ('task_completed')
    ORDER BY id DESC 
    LIMIT 20
""", (house_id,))
comments_messages = cursor.fetchall()

print(f"   📬 Messages qui apparaîtraient dans /comments: {len(comments_messages)}")
for msg in comments_messages:
    print(f"   - ID {msg['id']}: [{msg['message_type']}] {msg['content'][:50]}...")

conn.close()

print("\n" + "=" * 60)
print("✅ TEST TERMINÉ")
print("=" * 60)
print("\n🔍 Actions à faire:")
print("1. Vérifiez que le message apparaît ci-dessus")
print("2. Allez sur http://localhost:8000/comments")
print("3. Le message devrait être visible en ROSE")
