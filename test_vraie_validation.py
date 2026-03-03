#!/usr/bin/env python3
"""
Test simple pour déclencher une animation en validant une vraie tâche
"""

import sqlite3
from app import app, socketio, SOCKETIO_AVAILABLE

def test_real_task_validation():
    """Test avec validation d'une vraie tâche répétable"""
    
    print("🧪 === TEST VALIDATION TÂCHE RÉELLE ===")
    
    # 1. Trouver un utilisateur
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT email, house_id, name FROM users LIMIT 1')
    user = c.fetchone()
    conn.close()
    
    if not user:
        print("❌ Aucun utilisateur trouvé")
        return
        
    email, house_id, name = user
    print(f"👤 Test avec: {name or 'Sans nom'} ({email}) - Maison {house_id}")
    
    # 2. Validation via l'API interne (pas de doublon car tâche répétable)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user'] = email
            
        # Tâche "donner le biberon" qui peut être répétée
        response = client.post('/api/validate_task',
            json={
                'task_type': 'standard',
                'task_id': 1,
                'task_name': '🍼 Donner le biberon',
                'category': 'chambre_bebe',
                'player_email': email,
                'tracking_time': '15:30',
                'bottle_ml': '150'
            },
            headers={'Content-Type': 'application/json'})
            
        print(f"📤 Réponse API: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            print(f"✅ Tâche validée!")
            print(f"   Points gagnés: {data.get('points', '?')}")
            print(f"   Player: {data.get('player_name', '?')}")
            print(f"   Email: {data.get('player_email', '?')}")
            print(f"\n🎬 L'animation devrait s'être déclenchée automatiquement!")
            print(f"   Vérifiez dans le navigateur sur http://localhost:8000/menu")
        else:
            error_data = response.get_json()
            print(f"❌ Échec validation: {error_data}")

    # 3. Test WebSocket manuel en plus
    if SOCKETIO_AVAILABLE:
        print(f"\n📡 Test WebSocket direct en bonus...")
        test_data = {
            'player_email': email,
            'player_name': name or 'Test',
            'points': 50,
            'task_name': '⭐ Test Manuel Supplémentaire'
        }
        
        with app.app_context():
            room_name = f'house_{house_id}'
            socketio.emit('task_celebration', test_data, namespace='/', room=room_name)
            print(f"✅ WebSocket émis vers {room_name}")

if __name__ == "__main__":
    test_real_task_validation()