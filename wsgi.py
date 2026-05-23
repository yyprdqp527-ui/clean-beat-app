"""WSGI entry point."""
from gevent import monkey
monkey.patch_all()
from app import app, socketio, SOCKETIO_AVAILABLE
if SOCKETIO_AVAILABLE and socketio:
    application = socketio.sockio_mw
    # Bypass WhiteNoise pour que Socket.IO reçoive les requêtes directement
    socketio.sockio_mw.wsgi_app = app
else:
    application = app
