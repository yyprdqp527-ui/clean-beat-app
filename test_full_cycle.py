#!/usr/bin/env python3
"""
Test complet pour vérifier le cycle complet de l'animation :
1. Valider une vraie tâche via l'API
2. Vérifier l'émission WebSocket
3. Vérifier la réception côté client (si possible)
"""

import requests
import json
import time
import sqlite3
import os

def test_full_animation_cycle():
    """Test complet du cycle d'animation"""
    
    print("🎬 === TEST CYCLE COMPLET ANIMATION ===")
    
    # 1. Vérifier serveur
    try:
        resp = requests.get("http://localhost:8000/menu", timeout=5)
        print("✅ Serveur accessible")
    except:
        print("❌ Serveur non accessible")
        return
    
    # 2. Trouver utilisateur avec session valide
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT email, name, house_id FROM users WHERE email='pat@hotmail.com'")
    user = c.fetchone()
    conn.close()
    
    if not user:
        print("❌ Utilisateur test non trouvé")
        return
        
    email, name, house_id = user
    print(f"👤 Utilisateur test: {name or 'Sans nom'} ({email})")
    
    # 3. Test API validation tâche DIRECT avec serveur Flask
    print("\n🚀 === TEST VIA API DIRECTE ===")
    
    # Simuler l'appel API en important directement la fonction
    try:
        from app import app, api_validate_task, session, request
        
        test_data = {
            "task_type": "standard", 
            "task_id": 0,
            "task_name": "✨ Test API Direct",
            "category": "cuisine",
            "player_email": email
        }
        
        print(f"📝 Données test: {test_data}")
        
        # Créer une session fictive
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user'] = email
                
            # Faire l'appel API
            response = client.post('/api/validate_task',
                json=test_data,
                headers={'Content-Type': 'application/json'})
                
            print(f"📤 Réponse API: {response.status_code}")
            if response.status_code == 200:
                resp_data = response.get_json()
                print(f"✅ API Success: {resp_data}")
            else:
                print(f"❌ API Error: {response.data}")
                
    except Exception as e:
        print(f"❌ Erreur test API: {e}")
        import traceback
        traceback.print_exc()

    # 4. Test WebSocket direct (comme avant)
    print("\n📡 === TEST WEBSOCKET DIRECT ===")
    try:
        from app import socketio, app, SOCKETIO_AVAILABLE
        
        if SOCKETIO_AVAILABLE and socketio:
            test_data = {
                'player_email': email,
                'player_name': name or 'Test',
                'points': 30,
                'task_name': '🌟 Test WebSocket Direct'
            }
            
            with app.app_context():
                room_name = f'house_{house_id}'
                socketio.emit('task_celebration', test_data, namespace='/', room=room_name)
                print(f"✅ WebSocket émis vers room '{room_name}'")
                print(f"   Données: {test_data}")
        else:
            print("❌ WebSocket indisponible")
            
    except Exception as e:
        print(f"❌ Erreur WebSocket: {e}")
    
    # 5. Instructions pour tester côté client 
    print(f"\n🌐 === INSTRUCTIONS TEST CLIENT ===")
    print(f"1. Ouvrir http://localhost:8000/menu dans un navigateur")
    print(f"2. Se connecter avec l'email: {email}")
    print(f"3. Ouvrir la console développeur (F12)")
    print(f"4. Chercher les messages de debug commençant par 'WebSocket:'")
    print(f"5. Vérifier si l'événement 'task_celebration' est reçu")
    print(f"6. Vérifier si la fonction 'triggerCelebrationAnimation' est appelée")
    
    print(f"\n💡 Si ça ne marche toujours pas, vérifiez:")
    print(f"   - Que l'avatar avec email '{email}' est visible sur la page")
    print(f"   - Que la console ne montre pas d'erreurs JavaScript")
    print(f"   - Que WebSocket se connecte bien (message '🔌 WebSocket: Connecté')")

if __name__ == "__main__":
    test_full_animation_cycle()