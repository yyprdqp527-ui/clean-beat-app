#!/usr/bin/env python3
"""Script pour tester manuellement le système baby_tracking"""

import sqlite3
import requests
import json

# Test d'appel API
url = 'http://localhost:8000/api/validate_task'

# Simuler une validation de Lucien avec formulaire rempli
payload = {
    'task_type': 'standard',
    'task_id': 0,  # Index du biberon dans chambre_bebe
    'task_name': 'Donner le biberon',
    'category': 'chambre_bebe',
    'player_email': 'child_154_1769583879@cleanbeat.internal',
    'tracking_time': '09:30',
    'bottle_ml': '150',
    'observations': 'Test manuel - Bébé content'
}

print("🧪 Test de validation API avec baby tracking:")
print(f"📦 Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, timeout=10)
    print(f"📥 Response status: {response.status_code}")
    print(f"📥 Response body: {response.text}")
    
    if response.status_code == 200:
        print("✅ Validation réussie!")
        
        # Vérifier si le message a été créé
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute("""
            SELECT id, content, timestamp 
            FROM messages 
            WHERE sender_email = ? 
            AND message_type = 'baby_tracking'
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (payload['player_email'],))
        
        row = c.fetchone()
        if row:
            print(f"✅ Message créé: ID={row[0]}")
            print(f"   Content: {row[1]}")
            print(f"   Timestamp: {row[2]}")
        else:
            print("❌ Aucun message baby_tracking créé")
        
        conn.close()
    else:
        print("❌ Erreur de validation")
        
except Exception as e:
    print(f"❌ Erreur de connexion: {e}")