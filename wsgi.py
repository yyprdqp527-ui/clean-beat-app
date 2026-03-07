"""WSGI entry point for production (Gunicorn + gevent + Flask-SocketIO).

CRITIQUE: Le monkey patching est fait dans gunicorn_config.py (avant import de ce fichier)
pour garantir qu'il est fait en TOUT PREMIER, avant que gunicorn charge quoi que ce soit.
"""

import os
from app import app, socketio  # type: ignore

application = app
