#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_categorie_access():
    """Test l'accès aux pages de catégorie"""
    
    print("🔍 Test d'accès aux pages catégorie...")
    
    base_url = "http://192.168.1.156:8080"
    categories = ["cuisine", "salon", "chambre_parentale", "salle_bain", "garage"]
    
    for cat in categories:
        try:
            url = f"{base_url}/categorie/{cat}"
            print(f"\n📋 Test catégorie: {cat}")
            print(f"🌐 URL: {url}")
            
            response = requests.get(url, timeout=10)
            
            print(f"📊 Status: {response.status_code}")
            print(f"🔗 Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                content_length = len(response.text)
                print(f"✅ Succès - Contenu: {content_length} caractères")
                
                # Vérifier si c'est bien du HTML
                if "<!DOCTYPE html" in response.text or "<html" in response.text:
                    print("✅ HTML valide détecté")
                else:
                    print("❌ Réponse n'est pas du HTML")
                    print(f"Début du contenu: {response.text[:200]}...")
                    
            elif response.status_code == 302:
                print(f"🔄 Redirection vers: {response.headers.get('Location', 'Inconnue')}")
            elif response.status_code == 500:
                print("❌ Erreur serveur 500")
                print(f"Contenu de l'erreur: {response.text[:300]}...")
            else:
                print(f"❌ Erreur {response.status_code}")
                print(f"Contenu: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Impossible de se connecter à {url}")
            print(f"Erreur: {e}")
        except requests.exceptions.Timeout as e:
            print(f"⏱️ Timeout pour {url}")
            print(f"Erreur: {e}")
        except Exception as e:
            print(f"❌ Erreur inattendue pour {url}")
            print(f"Erreur: {e}")

def test_menu_access():
    """Test l'accès au menu principal"""
    
    print("\n🏠 Test d'accès au menu principal...")
    
    try:
        url = "http://192.168.1.156:8080/menu"
        response = requests.get(url, timeout=10)
        
        print(f"📊 Status menu: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Menu accessible")
        elif response.status_code == 302:
            print(f"🔄 Menu redirige vers: {response.headers.get('Location', 'Inconnue')}")
        else:
            print(f"❌ Problème menu: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur menu: {e}")

if __name__ == "__main__":
    test_categorie_access()
    test_menu_access()