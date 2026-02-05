#!/usr/bin/env python3
"""
Test de la messagerie en simulant une session utilisateur
"""
import requests
import json
from http.cookies import SimpleCookie

def test_messagerie():
    """Test l'affichage de la messagerie avec session simulée"""
    
    base_url = "http://192.168.1.149:8000"
    
    # Créer une session requests
    session = requests.Session()
    
    print("🧪 Test de la messagerie")
    print("=" * 50)
    
    # 1. Se connecter avec ag@me.com
    print("1. Connexion avec ag@me.com...")
    login_data = {
        'email': 'ag@me.com',
        'password': 'password123'  # Il faut le bon mot de passe
    }
    
    response = session.post(f"{base_url}/login", data=login_data)
    print(f"   Status: {response.status_code}")
    print(f"   Cookies: {dict(session.cookies)}")
    
    if response.status_code == 200 or response.status_code == 302:
        print("   ✅ Connexion réussie")
    else:
        print("   ❌ Échec de connexion")
        return
    
    # 2. Accéder à la messagerie
    print("\n2. Accès à la messagerie...")
    response = session.get(f"{base_url}/comments")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Accès à /comments réussi")
        
        # Chercher des messages dans la réponse HTML
        html = response.text
        if '🍼' in html or '👶' in html:
            print("   ✅ Des messages baby tracking semblent présents dans le HTML")
            # Compter les occurences
            biberon_count = html.count('🍼')
            couche_count = html.count('👶')
            print(f"       - Messages biberon (🍼): {biberon_count}")
            print(f"       - Messages couches (👶): {couche_count}")
        else:
            print("   ⚠️ Aucun message baby tracking visible dans le HTML")
            
        # Chercher la structure des messages
        if 'message-item' in html:
            message_count = html.count('message-item')
            print(f"   📬 Nombre d'éléments .message-item trouvés: {message_count}")
        else:
            print("   ❌ Aucun élément .message-item trouvé")
            
        if 'messages-list' in html:
            print("   ✅ Structure .messages-list présente")
        else:
            print("   ❌ Structure .messages-list manquante")
            
        # Chercher les messages vides
        if 'Aucun message pour le moment' in html or 'No messages' in html:
            print("   ❌ Message 'aucun message' détecté")
        
    elif response.status_code == 302:
        print(f"   ❌ Redirection vers: {response.headers.get('Location', 'inconnu')}")
        print("   ❌ Utilisateur pas connecté")
    else:
        print(f"   ❌ Erreur d'accès: {response.status_code}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_messagerie()