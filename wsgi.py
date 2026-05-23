"""WSGI entry point."""
from app import app, socketio, SOCKETIO_AVAILABLE
application = socketio.wsgi_app
