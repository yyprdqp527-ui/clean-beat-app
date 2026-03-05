"""WSGI entry point for production (Gunicorn + eventlet + Flask-SocketIO)."""
import eventlet
eventlet.monkey_patch()

import os
from app import app, socketio  # type: ignore

application = app
