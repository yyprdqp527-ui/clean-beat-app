"""WSGI entry point."""
from gevent import monkey
monkey.patch_all()

import os
from app import app, socketio, SOCKETIO_AVAILABLE
if SOCKETIO_AVAILABLE and socketio:
    def application(environ, start_response):
        return socketio(environ, start_response)
else:
    application = app
