"""WSGI entry point for production (Gunicorn + gevent + Flask-SocketIO).

CRITIQUE: Le monkey patching est fait dans gunicorn_config.py (avant import de ce fichier)
pour garantir qu'il est fait en TOUT PREMIER, avant que gunicorn charge quoi que ce soit.
"""

import os
from app import app, socketio, SOCKETIO_AVAILABLE  # type: ignore

# Pour gunicorn + gevent + Flask-SocketIO, on doit créer une application WSGI
# qui gère correctement les requêtes WebSocket via socketio
if SOCKETIO_AVAILABLE and socketio:
    # Créer un wrapper WSGI qui délègue à socketio pour les requêtes /socket.io/
    # et à app pour les requêtes HTTP normales
    def application(environ, start_response):
        """WSGI application wrapper for Flask-SocketIO."""
        # Flask-SocketIO gère automatiquement le routing entre HTTP et WebSocket
        # quand on appelle socketio comme une app WSGI
        return socketio(environ, start_response)
else:
    # Fallback si socketio n'est pas disponible
    application = app
