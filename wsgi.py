"""WSGI entry point."""
from gevent import monkey
monkey.patch_all()

import os
from app import app, socketio, SOCKETIO_AVAILABLE
application = app
