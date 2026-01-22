#!/usr/bin/env python3
"""
Script de diagnostic rapide pour CleanBeat
Vérifie la santé de l'application et de la base de données
"""

import sqlite3
import os
import sys
import time
import requests

DB = "users.db"

def test_database():
    """Teste la connexion et la configuration de la base de données"""
    print("🔍 Test de la base de données...")
    
    try:
        conn = sqlite3.connect(DB, timeout=30.0)
        
        # Vérifier le mode journal
        journal_mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
        print(f"  ✓ Mode journal: {journal_mode}")
        
        if journal_mode.lower() != 'wal':
            print(f"  ⚠️  Passage en mode WAL...")
            conn.execute('PRAGMA journal_mode=WAL')
            print(f"  ✓ Mode WAL activé")
        
        # Tester une requête simple
        start = time.time()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        query_time = (time.time() - start) * 1000
        
        print(f"  ✓ Utilisateurs: {user_count}")
        print(f"  ✓ Temps de requête: {query_time:.1f}ms")
        
        if query_time > 100:
            print(f"  ⚠️  Requête lente (> 100ms)")
        
        # Vérifier les récompenses
        c.execute("SELECT COUNT(*) FROM mystery_rewards")
        reward_count = c.fetchone()[0]
        print(f"  ✓ Récompenses: {reward_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_server():
    """Teste si le serveur Flask répond"""
    print("\n🌐 Test du serveur...")
    
    try:
        response = requests.get('http://127.0.0.1:8000/ping', timeout=5)
        if response.status_code == 200:
            print(f"  ✓ Serveur actif (200 OK)")
            return True
        else:
            print(f"  ⚠️  Code de réponse: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Serveur non accessible sur http://127.0.0.1:8000")
        print(f"  💡 Lancez: python3 app.py")
        return False
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_api_performance():
    """Teste la performance de l'API"""
    print("\n⚡ Test de performance API...")
    
    try:
        start = time.time()
        response = requests.get('http://127.0.0.1:8000/api/daily_tasks', timeout=10)
        response_time = (time.time() - start) * 1000
        
        if response.status_code == 200:
            print(f"  ✓ API daily_tasks: {response_time:.0f}ms")
            
            if response_time > 500:
                print(f"  ⚠️  Réponse lente (> 500ms)")
            elif response_time > 200:
                print(f"  ⚠️  Réponse moyenne (> 200ms)")
            else:
                print(f"  ✓ Performance excellente")
            
            return True
        else:
            print(f"  ❌ Erreur HTTP: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  ❌ Timeout (> 10s)")
        return False
    except Exception as e:
        print(f"  ⚠️  Erreur: {e}")
        return False

def check_files():
    """Vérifie les fichiers importants"""
    print("\n📁 Vérification des fichiers...")
    
    files = {
        'users.db': 'Base de données',
        'app.py': 'Application principale',
        'templates/menu.html': 'Template menu',
        'static/images/': 'Dossier images'
    }
    
    all_ok = True
    for file_path, description in files.items():
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                count = len([f for f in os.listdir(file_path) if not f.startswith('.')])
                print(f"  ✓ {description}: {count} éléments")
            else:
                size = os.path.getsize(file_path)
                size_mb = size / (1024 * 1024)
                print(f"  ✓ {description}: {size_mb:.1f}MB")
        else:
            print(f"  ❌ {description}: Manquant!")
            all_ok = False
    
    return all_ok

def main():
    """Exécute tous les tests"""
    print("="*50)
    print("🏥 Diagnostic CleanBeat")
    print("="*50)
    
    results = []
    
    # Tests
    results.append(("Base de données", test_database()))
    results.append(("Serveur Flask", test_server()))
    results.append(("Performance API", test_api_performance()))
    results.append(("Fichiers", check_files()))
    
    # Résumé
    print("\n" + "="*50)
    print("📊 Résumé")
    print("="*50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
    
    print(f"\n🎯 Score: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n✨ Tout fonctionne parfaitement!")
        return 0
    elif passed >= total * 0.5:
        print("\n⚠️  Quelques problèmes détectés")
        return 1
    else:
        print("\n❌ Problèmes critiques détectés")
        return 2

if __name__ == '__main__':
    sys.exit(main())
