#!/usr/bin/env python3
"""
Tester l'API /api/active_suspicions pour vérifier qu'elle retourne bien les données
"""
import requests

# Test avec la session de Marcel (house_id 150)
session = requests.Session()

# Connexion avec Marcel
login_data = {
    'email': 'gaelledavalix@gmail.com',  # Marcel
    'password': 'Doudou2004'
}

resp = session.post('http://127.0.0.1:8000/login', data=login_data)
print(f"Connexion Marcel : {resp.status_code}")

# Appel à l'API active_suspicions
resp = session.get('http://127.0.0.1:8000/api/active_suspicions')
print(f"\nAPI /api/active_suspicions : {resp.status_code}")
print(f"Données : {resp.json()}")

# Devrait montrer Emma et Lucas avec des suspicions actives
