"""WSGI entry point for production (Gunicorn + eventlet + Flask-SocketIO)."""

from app import app, socketio  # type: ignore

# Gunicorn + eventlet gère les WebSockets automatiquement via le WSGI standard
application = app
