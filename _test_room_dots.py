#!/usr/bin/env python3
"""Test: vérifier room-mission-dot et room-baby-dot dans le HTML rendu"""
import sys, os, re
os.chdir('/Users/anne-gaelledaval/Downloads/Appli web-2')
sys.path.insert(0, '.')
os.environ['FLASK_ENV'] = 'development'
from app import app

app.config['TESTING'] = True
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user'] = 'agdaval@yahoo.fr'
    
    response = client.get('/menu')
    html = response.data.decode('utf-8')
    
    # 1. Chercher room-mission-dot (toutes les variantes)
    for pattern_name, pattern in [
        ('room-mission-dot class', r'room-mission-dot[^"]*"[^>]*>[^<]*</'),
        ('room-mission-dot anywhere', r'room-mission-dot'),
        ('room-new-mission-badge', r'room-new-mission-badge'),
        ('data-category', r'data-category="[^"]*"'),
        ('room-card-visual', r'room-card-visual'),
        ('chambre_ado', r'chambre_ado'),
    ]:
        matches = re.findall(pattern, html)
        print(f"{pattern_name}: {len(matches)} match(es)")
        for m in matches[:5]:
            print(f"  -> {m[:120]}")
    
    # 2. Trouver la zone des room cards (autour de room-card)
    all_room_cards = re.findall(r'<a[^>]*class="room-card"[^>]*>', html)
    print(f"\nRoom cards: {len(all_room_cards)}")
    
    # 3. Chercher le contenu autour de chambre_ado
    idx = html.find('chambre_ado')
    if idx >= 0:
        print(f"\nchambre_ado context (pos {idx}):")
        print(html[idx-200:idx+400])
    else:
        print("\nchambre_ado: NOT FOUND")
    
    # 4. Check push-notif-banner
    push_banner = re.search(r'push-notif-banner[^"]*"[^>]*>', html)
    if push_banner:
        print(f"\nPush banner: {push_banner.group(0)[:200]}")
