#!/usr/bin/env python3
"""
Script pour tester l'accès aux commentaires avec simulation de session
"""

import requests
import json

def test_comments_with_session():
    """Test des commentaires avec simulation de session"""
    
    # URL de base
    base_url = "http://192.168.1.149:8000"
    
    # Créer une session
    session = requests.Session()
    
    # 1. Essayer de se connecter
    print("🔐 Tentative de connexion...")
    login_data = {
        'email': 'ag@me.com',
        'password': 'test'
    }
    
    response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
    if response.status_code == 302:  # Redirection = success
        print("   ✅ Connexion réussie")
        
        # 2. Accéder aux commentaires
        print("\n📨 Accès aux commentaires...")
        comments_response = session.get(f"{base_url}/comments")
        print(f"   Status: {comments_response.status_code}")
        
        if comments_response.status_code == 200:
            print("   ✅ Page commentaires accessible")
            # Chercher les messages baby_tracking dans le HTML
            html_content = comments_response.text
            
            if 'message-baby-tracking' in html_content:
                print("   ✅ Messages baby_tracking trouvés dans le HTML!")
                # Compter les occurrences
                count = html_content.count('message-baby-tracking')
                print(f"      Nombre d'occurrences: {count}")
            else:
                print("   ❌ Aucun message baby_tracking dans le HTML")
                
            if '🍼' in html_content:
                biberon_count = html_content.count('🍼')
                print(f"   🍼 Emojis biberon trouvés: {biberon_count}")
            
            # Sauvegarder le HTML pour inspection
            with open('comments_debug.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print("   💾 HTML sauvegardé dans comments_debug.html")
            
        else:
            print(f"   ❌ Erreur accès commentaires: {comments_response.status_code}")
            
    else:
        print(f"   ❌ Échec connexion: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")

if __name__ == "__main__":
    test_comments_with_session()