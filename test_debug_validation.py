#!/usr/bin/env python3
"""
Test pour valider une tâche et surveiller les données WebSocket
"""

import sqlite3
from app import app

def test_task_validation_debug():
    """Test avec debug des données exactes"""
    
    print("🧪 === TEST VALIDATION AVEC DEBUG ===")
    
    # 1. Trouver utilisateurs
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT email, house_id, name FROM users ORDER BY id LIMIT 3')
    users = c.fetchall()
    conn.close()
    
    if not users:
        print("❌ Aucun utilisateur trouvé")
        return
        
    print(f"👥 Utilisateurs disponibles:")
    for i, (email, house_id, name) in enumerate(users):
        print(f"   {i+1}. {name or 'Sans nom'} ({email}) - Maison {house_id}")
    
    # Test avec le premier utilisateur
    email, house_id, name = users[0]
    print(f"\n🎯 Test avec: {name or 'Sans nom'} ({email})")
    
    # 2. Validation d'une tâche qui peut être répétée plusieurs fois
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user'] = email
            
        # Tâche "éponge" qui peut être répétée
        response = client.post('/api/validate_task',
            json={
                'task_type': 'standard',
                'task_id': 1,  
                'task_name': 'Passer l\'éponge',
                'category': 'cuisine',
                'player_email': email
            },
            headers={'Content-Type': 'application/json'})
            
        print(f"\n📤 Validation tâche 'Passer l'éponge'")
        print(f"Statut: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            print(f"✅ Succès!")
            print(f"   📧 Email retourné: {data.get('player_email')}")
            print(f"   👤 Nom retourné: {data.get('player_name')}")
            print(f"   🎯 Points retournés: {data.get('points')}")
            print(f"   📋 Tâche: {data.get('task_name')}")
            print(f"   ⏰ Timestamp: {data.get('timestamp')}")
            
            print(f"\n🎬 L'animation devrait apparaître sur l'avatar de {data.get('player_name')} avec {data.get('points')} points")
            print(f"🌐 Vérifiez la console du navigateur sur http://localhost:8000/menu")
            
        else:
            try:
                error_data = response.get_json()
                print(f"❌ Erreur: {error_data}")
            except:
                print(f"❌ Erreur HTTP {response.status_code}: {response.data}")

if __name__ == "__main__":
    test_task_validation_debug()