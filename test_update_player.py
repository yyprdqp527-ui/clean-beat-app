#!/usr/bin/env python3
"""
Test de la fonctionnalité de modification de profil
"""
from app import app
import json

def test_update_player():
    """Tester la mise à jour d'un joueur"""
    
    with app.test_client() as client:
        # Se connecter
        with client.session_transaction() as sess:
            sess['user'] = 'pat@hotmail.com'
        
        print("🧪 TEST 1: Modification du nom")
        print("=" * 60)
        
        # Test 1: Changer le nom
        response = client.post('/update_player', data={
            'email': 'pat@hotmail.com',
            'name': 'Patrick',
            'avatar_type': ''
        })
        
        print(f"Statut: {response.status_code}")
        if response.status_code == 200:
            result = response.get_json()
            print(f"Succès: {result.get('success')}")
            if not result.get('success'):
                print(f"Erreur: {result.get('error')}")
        else:
            print(f"Erreur HTTP: {response.data}")
        
        print()
        print("🧪 TEST 2: Modification de l'avatar emoji")
        print("=" * 60)
        
        # Test 2: Changer l'avatar en emoji
        response = client.post('/update_player', data={
            'email': 'pat@hotmail.com',
            'name': 'Patrick',
            'avatar_type': 'emoji',
            'avatar': '👨'
        })
        
        print(f"Statut: {response.status_code}")
        if response.status_code == 200:
            result = response.get_json()
            print(f"Succès: {result.get('success')}")
            if not result.get('success'):
                print(f"Erreur: {result.get('error')}")
        else:
            print(f"Erreur HTTP: {response.data}")
        
        print()
        print("🧪 TEST 3: Modification de l'avatar DiceBear")
        print("=" * 60)
        
        # Test 3: Changer l'avatar en DiceBear
        response = client.post('/update_player', data={
            'email': 'pat@hotmail.com',
            'name': 'Patrick',
            'avatar_type': 'dicebear',
            'avatar': 'patrick123',
            'avatar_style': 'avataaars'
        })
        
        print(f"Statut: {response.status_code}")
        if response.status_code == 200:
            result = response.get_json()
            print(f"Succès: {result.get('success')}")
            if not result.get('success'):
                print(f"Erreur: {result.get('error')}")
        else:
            print(f"Erreur HTTP: {response.data}")
        
        print()
        print("✅ Tests terminés")
        print()
        print("Vérification dans la base de données:")
        
        import sqlite3
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT name, avatar, avatar_url, avatar_style FROM users WHERE email='pat@hotmail.com'")
        row = c.fetchone()
        if row:
            print(f"  Nom: {row[0]}")
            print(f"  Avatar: {row[1]}")
            print(f"  Avatar URL: {row[2]}")
            print(f"  Avatar Style: {row[3]}")
        conn.close()

if __name__ == "__main__":
    test_update_player()
