#!/usr/bin/env python3
"""
🔍 Script de vérification de l'installation WebSocket
"""

import sys

print("=" * 60)
print("🔍 VÉRIFICATION INSTALLATION WEBSOCKET")
print("=" * 60)

# 1. Vérifier Flask
try:
    import flask
    print(f"✅ Flask installé (version {flask.__version__})")
except ImportError:
    print("❌ Flask NON installé")
    sys.exit(1)

# 2. Vérifier Flask-SocketIO
try:
    import flask_socketio
    print(f"✅ Flask-SocketIO installé")
except ImportError:
    print("❌ Flask-SocketIO NON installé")
    print("   Installation: pip3 install flask-socketio")
    sys.exit(1)

# 3. Vérifier python-socketio
try:
    import socketio
    print(f"✅ python-socketio installé")
except ImportError:
    print("❌ python-socketio NON installé")
    print("   Installation: pip3 install python-socketio")
    sys.exit(1)

# 4. Vérifier python-engineio
try:
    import engineio
    print(f"✅ python-engineio installé")
except ImportError:
    print("⚠️  python-engineio NON installé (normalement installé avec python-socketio)")

# 5. Vérifier les imports depuis app.py
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    print("✅ Tous les imports nécessaires sont disponibles")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

# 6. Tester la création d'une instance SocketIO
try:
    from flask import Flask
    test_app = Flask(__name__)
    test_socketio = SocketIO(test_app, cors_allowed_origins="*")
    print("✅ Instance SocketIO créée avec succès")
except Exception as e:
    print(f"❌ Erreur création SocketIO: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 TOUTES LES VÉRIFICATIONS SONT PASSÉES !")
print("=" * 60)
print("\n✨ Votre application est prête pour le temps réel !")
print("\n📝 Prochaines étapes:")
print("   1. Démarrer le serveur: python3 app.py")
print("   2. Ouvrir 2 navigateurs/appareils")
print("   3. Valider une tâche et observer la synchronisation")
print("\n📚 Documentation:")
print("   - WEBSOCKET_TEMPS_REEL.md (guide technique)")
print("   - DEMARRAGE_WEBSOCKET.md (guide rapide)")
print("   - RESUME_WEBSOCKET.md (résumé)")
