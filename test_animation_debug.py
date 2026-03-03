#!/usr/bin/env python3
"""
Script de debug pour tester l'animation des étoiles.
"""

import requests
import json
import time
import sqlite3

def test_animation():
    """Test l'animation d'étoiles via l'API"""
    
    print("🔍 === DIAGNOSTIC ANIMATION ÉTOILES ===")
    
    # 1. Vérifier la connexion serveur
    try:
        resp = requests.get("http://localhost:8000/menu", timeout=5)
        if resp.status_code == 200:
            print("✅ Serveur accessible")
        else:
            print(f"❌ Serveur problème: HTTP {resp.status_code}")
            return
    except Exception as e:
        print(f"❌ Serveur non accessible: {e}")
        return
    
    # 2. Vérifier les utilisateurs disponibles
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT email, name, house_id FROM users LIMIT 3")
    users = c.fetchall()
    conn.close()
    
    print(f"\n👥 Utilisateurs trouvés: {len(users)}")
    for i, (email, name, house_id) in enumerate(users):
        print(f"   {i+1}. {name or 'Sans nom'} ({email}) - Maison {house_id}")
    
    if not users:
        print("❌ Aucun utilisateur trouvé")
        return
    
    # Prendre le premier utilisateur
    test_email, test_name, house_id = users[0]
    print(f"\n🎯 Test avec: {test_name or 'Sans nom'} ({test_email})")
    
    # 3. Simuler une validation de tâche via l'API (simulation sans session)
    # Création d'une requête simple avec les bons en-têtes
    test_payload = {
        "task_type": "standard",
        "task_id": 0,
        "task_name": "✨ Test animation étoiles",
        "category": "cuisine",
        "player_email": test_email
    }
    
    print("\n📡 Test émission WebSocket directe...")
    
    # 4. Test direct avec app context (plus fiable que l'API sans session)
    try:
        from app import socketio, app, SOCKETIO_AVAILABLE
        
        if SOCKETIO_AVAILABLE and socketio:
            test_data = {
                'player_email': test_email,
                'player_name': test_name or 'Test',
                'points': 25,
                'task_name': '✨ Test animation étoiles ⭐'
            }
            
            print(f"🚀 Émission task_celebration...")
            with app.app_context():
                # Émettre vers la room de la maison
                room_name = f'house_{house_id}'
                socketio.emit('task_celebration', test_data, namespace='/', room=room_name)
                print(f"✨ Événement émis vers room '{room_name}'!")
                print(f"   📧 Email: {test_data['player_email']}")
                print(f"   👤 Nom: {test_data['player_name']}")  
                print(f"   🎯 Points: {test_data['points']}")
                print(f"   📋 Tâche: {test_data['task_name']}")
                
                print(f"\n✅ Si un navigateur est ouvert sur le menu, l'animation devrait se déclencher!")
                print(f"🔍 Vérifiez la console du navigateur pour les messages de debug")
                
        else:
            print("❌ WebSocket non disponible")
            
    except Exception as e:
        print(f"❌ Erreur WebSocket: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_animation()