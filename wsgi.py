"""WSGI entry point."""
from gevent import monkey
monkey.patch_all()
from app import app, socketio, SOCKETIO_AVAILABLE

if SOCKETIO_AVAILABLE and socketio:
    application = socketio.middleware(app)
else:
    application = app
