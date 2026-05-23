"""WSGI entry point."""
from gevent import monkey
monkey.patch_all()

from app import app, socketio, SOCKETIO_AVAILABLE
application = app
