#!/usr/bin/env python3
"""Test simple pour vérifier les en-têtes CORS"""

import requests

try:
    response = requests.get('http://localhost:8000/api/players_points')
    
    print("=== Test CORS ===")
    print(f"Status: {response.status_code}")
    print("\n=== En-têtes de réponse ===")
    for header, value in response.headers.items():
        if 'access-control' in header.lower() or 'cors' in header.lower():
            print(f"✅ {header}: {value}")
        else:
            print(f"   {header}: {value}")
    
    print(f"\n=== Contenu ===")
    print(response.text)
    
    # Test avec Origin
    print("\n=== Test avec Origin ===")
    headers = {'Origin': 'http://localhost:8000'}
    response2 = requests.get('http://localhost:8000/api/players_points', headers=headers)
    
    print("En-têtes CORS avec Origin:")
    for header, value in response2.headers.items():
        if 'access-control' in header.lower():
            print(f"✅ {header}: {value}")

except Exception as e:
    print(f"❌ Erreur: {e}")