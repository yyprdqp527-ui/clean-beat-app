#!/usr/bin/env python3
"""
Test pour diagnostiquer le problème de broadcast WebSocket
"""
import sqlite3
from app import app, socketio, SOCKETIO_AVAILABLE

def test_websocket_broadcast():
    """Teste l'émission WebSocket avec broadcast"""
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Récupérer tous les joueurs d'une maison
    c.execute("""
        SELECT u.email, u.name, u.house_id
        FROM users u
        WHERE u.house_id IS NOT NULL
        LIMIT 2
    """)
    
    users = c.fetchall()
    conn.close()
    
    if len(users) < 2:
        print("❌ Il faut au moins 2 joueurs dans une maison pour tester")
        return
    
    player1_email, player1_name, house_id = users[0]
    player2_email, player2_name, _ = users[1]
    
    print(f"🎯 Test de broadcast WebSocket")
    print(f"   House ID: {house_id}")
    print(f"   Joueur 1: {player1_name} ({player1_email})")
    print(f"   Joueur 2: {player2_name} ({player2_email})")
    print()
    
    if not SOCKETIO_AVAILABLE:
        print("❌ WebSocket non disponible")
        return
    
    # Test 1: Émission SANS broadcast
    print("📡 Test 1: Émission SANS broadcast=True")
    with app.app_context():
        room_name = f'house_{house_id}'
        socketio.emit('test_event_no_broadcast', {
            'message': 'Test SANS broadcast',
            'updated_player': player1_email
        }, namespace='/', room=room_name)
        print(f"   ✅ Événement 'test_event_no_broadcast' émis vers room '{room_name}'")
    
    print()
    
    # Test 2: Émission AVEC broadcast
    print("📡 Test 2: Émission AVEC broadcast=True")
    with app.app_context():
        room_name = f'house_{house_id}'
        socketio.emit('test_event_with_broadcast', {
            'message': 'Test AVEC broadcast',
            'updated_player': player1_email
        }, namespace='/', room=room_name, broadcast=True)
        print(f"   ✅ Événement 'test_event_with_broadcast' émis vers room '{room_name}' avec broadcast=True")
    
    print()
    print("📌 INSTRUCTIONS:")
    print("1. Ouvrez 2 navigateurs avec les 2 joueurs connectés sur /menu")
    print("2. Ouvrez la console (F12) dans les 2 navigateurs")
    print("3. Vérifiez quels événements sont reçus:")
    print("   - Si les 2 reçoivent 'players_points_update' → Le problème n'est PAS le broadcast")
    print("   - Si 1 seul reçoit → Le broadcast manque!")
    print()
    print("4. Pour écouter les événements de test, ajoutez dans la console:")
    print("   socket.on('test_event_no_broadcast', (d) => console.log('📨 Sans broadcast:', d));")
    print("   socket.on('test_event_with_broadcast', (d) => console.log('📨 Avec broadcast:', d));")

if __name__ == "__main__":
    test_websocket_broadcast()
