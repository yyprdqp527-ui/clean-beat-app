"""WSGI entry point."""
import os
from app import app, socketio, SOCKETIO_AVAILABLE
application = app
