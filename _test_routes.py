#!/usr/bin/env python3
"""Test rapide des routes critiques"""
import requests, warnings, json
warnings.filterwarnings('ignore')
s = requests.Session()

# Login
r = s.post('http://127.0.0.1:8000/login', data={
    'email': 'agdaval@me.com',
    'password': 'test1234'
}, allow_redirects=False)
print(f'Login: {r.status_code} -> {r.headers.get("Location","")}')

# Test 1: Validate task via API
print("\n=== TEST 1: /api/validate_task ===")
r = s.post('http://127.0.0.1:8000/api/validate_task', 
    json={
        'task_type': 'standard',
        'task_id': 0,
        'task_name': 'Faire le lit',
        'category': 'chambre',
        'player_email': 'agdaval@me.com'
    })
print(f'Status: {r.status_code}')
try:
    data = r.json()
    print(f'Response: {json.dumps(data, ensure_ascii=False)}')
except Exception as e:
    print(f'JSON error: {e}')
    print(f'Text: {r.text[:300]}')

# Test 2: manage_players page
print("\n=== TEST 2: /manage_players ===")
r = s.get('http://127.0.0.1:8000/manage_players')
print(f'Status: {r.status_code}, length={len(r.text)}')

# Test 3: update_player (avatar change)
print("\n=== TEST 3: /update_player ===")
r = s.post('http://127.0.0.1:8000/update_player', data={
    'email': 'agdaval@me.com',
    'name': 'Anne-Gaelle',
    'avatar_type': 'dicebear',
    'avatar': 'TestSeed123',
    'avatar_style': 'adventurer'
})
print(f'Status: {r.status_code}')
try:
    print(f'Response: {r.json()}')
except Exception as e:
    print(f'JSON error: {e}')
    print(f'Text: {r.text[:300]}')

print("\n=== DONE ===")
