#!/usr/bin/env python3
"""Test pour diagnostiquer le problème CORS"""

import requests

# Test simple de la route avec debug détaillé
print("=== Test diagnostic CORS ===")

try:
    session = requests.Session()
    
    # Test sans session (cas actuel)
    print("1. Test sans authentification:")
    response = requests.get('http://localhost:8000/api/players_points')
    print(f"   Status: {response.status_code}")
    print(f"   Content-Length: {response.headers.get('Content-Length')}")
    print(f"   Content-Type: {response.headers.get('Content-Type')}")
    print(f"   Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NON TROUVÉ')}")
    print(f"   Contenu: {response.text[:50]}...")
    
    # Afficher TOUS les en-têtes
    print("   Tous les en-têtes:")
    for header, value in response.headers.items():
        print(f"     {header}: {value}")

except Exception as e:
    print(f"❌ Erreur: {e}")