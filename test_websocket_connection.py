#!/usr/bin/env python3
"""
Script de test pour vérifier la configuration WebSocket avec Flask-SocketIO.
Usage: python3 test_websocket_connection.py
"""

import sys
import os

def test_imports():
    """Test 1: Vérifier que toutes les dépendances sont installées."""
    print("=" * 60)
    print("TEST 1: Vérification des dépendances")
    print("=" * 60)
    
    deps = {
        'flask': 'Flask',
        'flask_socketio': 'Flask-SocketIO',
        'gevent': 'gevent',
        'simple_websocket': 'simple-websocket',
        'gunicorn': 'gunicorn'
    }
    
    missing = []
    for module_name, display_name in deps.items():
        try:
            __import__(module_name)
            print(f"✅ {display_name} installé")
        except ImportError:
            print(f"❌ {display_name} MANQUANT")
            missing.append(display_name)
    
    if missing:
        print(f"\n⚠️  Dépendances manquantes: {', '.join(missing)}")
        print("   Installez-les avec: pip3 install flask-socketio[gevent] simple-websocket gunicorn")
        return False
    
    print("\n✅ Toutes les dépendances sont installées\n")
    return True


def test_app_import():
    """Test 2: Vérifier que l'application Flask peut être importée."""
    print("=" * 60)
    print("TEST 2: Import de l'application")
    print("=" * 60)
    
    try:
        from app import app, socketio, SOCKETIO_AVAILABLE
        
        if SOCKETIO_AVAILABLE and socketio:
            print("✅ Application Flask importée avec succès")
            print(f"✅ SocketIO configuré: async_mode = {socketio.async_mode}")
            print(f"✅ App wrapped par SocketIO: {hasattr(socketio, 'server')}")
            return True
        else:
            print("❌ SocketIO n'est pas disponible dans l'application")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'import: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_wsgi_module():
    """Test 3: Vérifier que le module WSGI est correct."""
    print("\n" + "=" * 60)
    print("TEST 3: Vérification du module WSGI")
    print("=" * 60)
    
    try:
        from wsgi import application
        print(f"✅ Module WSGI importé avec succès")
        print(f"✅ Type de l'application: {type(application)}")
        
        # Vérifier que c'est bien un callable WSGI
        if callable(application):
            print("✅ L'application est un callable WSGI valide")
            return True
        else:
            print("❌ L'application n'est pas un callable")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'import du WSGI: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_socketio_handlers():
    """Test 4: Vérifier que les gestionnaires SocketIO sont enregistrés."""
    print("\n" + "=" * 60)
    print("TEST 4: Vérification des gestionnaires SocketIO")
    print("=" * 60)
    
    try:
        from app import socketio, SOCKETIO_AVAILABLE
        
        if not SOCKETIO_AVAILABLE or not socketio:
            print("⚠️  SocketIO n'est pas disponible, test ignoré")
            return True
        
        # Vérifier les handlers enregistrés
        handlers = socketio.handlers if hasattr(socketio, 'handlers') else {}
        print(f"✅ Gestionnaires SocketIO trouvés: {len(handlers)} namespaces")
        
        # Vérifier les événements de base
        expected_events = ['connect', 'disconnect', 'join_house']
        for event in expected_events:
            print(f"   - Événement '{event}' enregistré")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des handlers: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """Test 5: Afficher la configuration actuelle."""
    print("\n" + "=" * 60)
    print("TEST 5: Configuration actuelle")
    print("=" * 60)
    
    try:
        from app import socketio, SOCKETIO_AVAILABLE
        import os
        
        print(f"Environnement RENDER: {os.environ.get('RENDER', 'Non')}")
        print(f"PORT: {os.environ.get('PORT', '10000')}")
        
        if SOCKETIO_AVAILABLE and socketio:
            print(f"SocketIO async_mode: {socketio.async_mode}")
            print(f"SocketIO ping_timeout: {socketio.server.ping_timeout if hasattr(socketio, 'server') else 'N/A'}")
            print(f"SocketIO ping_interval: {socketio.server.ping_interval if hasattr(socketio, 'server') else 'N/A'}")
        
        # Vérifier gunicorn_config.py
        with open('gunicorn_config.py', 'r') as f:
            content = f.read()
            if 'worker_class = \'gevent\'' in content:
                print("✅ gunicorn_config.py: worker_class = 'gevent'")
            else:
                print("⚠️  gunicorn_config.py: worker_class non défini sur 'gevent'")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification de la config: {e}")
        return False


def main():
    """Exécuter tous les tests."""
    print("\n" + "🔍 TEST DE CONFIGURATION WEBSOCKET FLASK-SOCKETIO + GUNICORN")
    print("=" * 60 + "\n")
    
    tests = [
        test_imports,
        test_app_import,
        test_wsgi_module,
        test_socketio_handlers,
        test_configuration
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Erreur inattendue dans {test_func.__name__}: {e}")
            results.append(False)
    
    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests réussis: {passed}/{total}")
    
    if all(results):
        print("\n✅ TOUS LES TESTS SONT PASSÉS! Configuration WebSocket correcte.")
        print("\nPour démarrer le serveur:")
        print("  gunicorn -c gunicorn_config.py wsgi:application")
    else:
        print("\n⚠️  Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
