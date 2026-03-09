#!/usr/bin/env python3
"""Test validation d'une nouvelle tâche (pas doublon)"""
import requests, warnings, json
warnings.filterwarnings('ignore')
s = requests.Session()

# Login
r = s.post('http://127.0.0.1:8000/login', data={
    'email': 'agdaval@me.com',
    'password': 'test1234'
}, allow_redirects=False)
print(f'Login: {r.status_code}')

# Validate a task that hasn't been done today
import time
unique_name = f'Passer aspirateur {int(time.time())}'
print(f"\n=== Validation tâche: {unique_name} ===")
r = s.post('http://127.0.0.1:8000/api/validate_task', 
    json={
        'task_type': 'standard',
        'task_id': 1,
        'task_name': unique_name,
        'category': 'chambre',
        'player_email': 'agdaval@me.com'
    })
print(f'Status: {r.status_code}')
try:
    data = r.json()
    print(f'Response: {json.dumps(data, ensure_ascii=False, indent=2)}')
    if data.get('success'):
        print(f'✅ Points gagnés: {data.get("points")}')
    else:
        print(f'❌ Erreur: {data.get("error")}')
except Exception as e:
    print(f'Erreur JSON: {e}')
    print(f'Text: {r.text[:300]}')
