#!/usr/bin/env python3
"""
Test: simuler une requête HTTP vers /menu pour vérifier le rendu des badges.
Utilise le test client Flask pour éviter de lancer un serveur.
"""
import sys
import os
os.chdir('/Users/anne-gaelledaval/Downloads/Appli web-2')

# Import the Flask app
sys.path.insert(0, '.')
os.environ['FLASK_ENV'] = 'development'

from app import app

app.config['TESTING'] = True

with app.test_client() as client:
    # Login as agdaval@yahoo.fr
    with client.session_transaction() as sess:
        sess['user'] = 'agdaval@yahoo.fr'
    
    # Request /menu
    response = client.get('/menu')
    html = response.data.decode('utf-8')
    
    # Search for badge-related content
    import re
    
    # 1. Check debug banner SSR values
    ssr_match = re.search(r'SSR:.*?MSG=(.*?)\s+BABY=(.*?)\s+CRS=(.*?)\s+MISS=(.*?)\s+players=(\d+)', html)
    if ssr_match:
        print(f"DEBUG BANNER SSR: MSG={ssr_match.group(1)} BABY={ssr_match.group(2)} CRS={ssr_match.group(3)} MISS={ssr_match.group(4)} players={ssr_match.group(5)}")
    else:
        print("DEBUG BANNER: NOT FOUND or different format")
        # Try to find it anyway
        dbg = re.search(r'SSR:.*?<br', html)
        if dbg:
            print(f"  Found partial: {dbg.group(0)[:200]}")
    
    # 2. Check bottomNavMessagesBadge
    badge_match = re.search(r'id="bottomNavMessagesBadge"[^>]*>(.*?)</span>', html)
    if badge_match:
        # Get the full match with style
        full_match = re.search(r'id="bottomNavMessagesBadge"[^>]*', html)
        print(f"\nMSG BADGE HTML: {full_match.group(0)}")
        print(f"MSG BADGE TEXT: '{badge_match.group(1)}'")
        
        if 'display:none' in full_match.group(0):
            print("MSG BADGE: HIDDEN (display:none)")
        else:
            print("MSG BADGE: VISIBLE!")
    else:
        print("\nMSG BADGE: NOT FOUND IN HTML!")
    
    # 3. Check bottomNavCoursesBadge
    crs_match = re.search(r'id="bottomNavCoursesBadge"[^>]*>(.*?)</span>', html)
    if crs_match:
        full_crs = re.search(r'id="bottomNavCoursesBadge"[^>]*', html)
        print(f"\nCRS BADGE HTML: {full_crs.group(0)}")
        if 'display:none' in full_crs.group(0):
            print("CRS BADGE: HIDDEN")
        else:
            print("CRS BADGE: VISIBLE!")
    
    # 4. Check room-baby-dot
    baby_match = re.search(r'id="room-baby-dot"[^>]*>(.*?)</span>', html)
    if baby_match:
        full_baby = re.search(r'id="room-baby-dot"[^>]*', html)
        print(f"\nBABY DOT HTML: {full_baby.group(0)}")
        if 'display:none' in full_baby.group(0):
            print("BABY DOT: HIDDEN")
        else:
            print("BABY DOT: VISIBLE!")
    
    # 5. Check mission dots
    mission_dots = re.findall(r'room-mission-dot[^>]*>(\d*)</span>', html)
    visible_missions = [m for m in re.findall(r'class="room-mission-dot"[^>]*', html) if 'display:none' not in m]
    print(f"\nMISSION DOTS: {len(mission_dots)} total, {len(visible_missions)} visible")
    
    # 6. Check cw-wrap exists
    if 'class="cw-wrap"' in html:
        print("\n.cw-wrap NAV BAR: EXISTS")
    else:
        print("\n.cw-wrap NAV BAR: MISSING!")
    
    # 7. Check IIFE Jinja values
    iife_match = re.search(r'unread_received:\s*(\d+).*?unread_baby:\s*(\d+).*?courses_pending_count:\s*(\d+).*?pending_missions_count:\s*(\d+)', html, re.DOTALL)
    if iife_match:
        print(f"\nIIFE VALUES: recv={iife_match.group(1)} baby={iife_match.group(2)} crs={iife_match.group(3)} miss={iife_match.group(4)}")
    
    print(f"\nResponse status: {response.status_code}")
    print(f"HTML length: {len(html)} chars")
