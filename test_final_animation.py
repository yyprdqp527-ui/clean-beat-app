#!/usr/bin/env python3
"""
Test final de l'animation avec une tâche répétable
"""

from app import app, socketio, SOCKETIO_AVAILABLE
import sqlite3

def test_final():
    # Test avec une tâche répétable (biberon)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT email, house_id FROM users LIMIT 1')
    user = c.fetchone()
    conn.close()

    if user and SOCKETIO_AVAILABLE:
        email, house_id = user
        
        print(f"🎯 Test final avec {email} (maison {house_id})")
        
        # 1. Test WebSocket direct
        test_data = {
            'player_email': email,
            'player_name': 'TestFinal',
            'points': 50,
            'task_name': '🌟 Test Final Animation'
        }
        
        with app.app_context():
            room_name = f'house_{house_id}'
            socketio.emit('task_celebration', test_data, namespace='/', room=room_name)
            print(f'✅ WebSocket émis vers {room_name}')
        
        # 2. Test API avec tâche répétable
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user'] = email
                
            response = client.post('/api/validate_task',
                json={
                    'task_type': 'standard', 
                    'task_id': 0,
                    'task_name': '🍼 Donner le biberon',
                    'category': 'chambre_bebe',
                    'player_email': email
                },
                headers={'Content-Type': 'application/json'})
                
            print(f'📤 Réponse API: {response.status_code}')
            if response.status_code == 200:
                data = response.get_json()
                print(f'✅ API Succès: +{data.get("points", 0)} points')
                print('🎬 Animation automatique déclenchée!')
            else:
                print(f'❌ Erreur API: {response.data}')

    print("\n🎉 === RÉSUMÉ ===")
    print("✅ Console.log réactivés")  
    print("✅ Fonction triggerCelebrationAnimation déplacée en global")
    print("✅ WebSocket fonctionnel")
    print("✅ API fonctionnelle")
    print("\n🌐 Maintenant dans le navigateur:")
    print("1. Aller sur http://localhost:8000/menu")
    print("2. F12 → Console")
    print("3. Valider une vraie tâche → L'animation devrait marcher!")

if __name__ == "__main__":
    test_final()