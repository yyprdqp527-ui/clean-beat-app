"""WSGI entry point for production (Gunicorn + gevent + Flask-SocketIO).

CRITIQUE: Utilise UNIQUEMENT gevent (pas de fallback eventlet) pour éviter
les conflits de monkey patching et les erreurs "cannot release un-acquired lock".
"""

# ⚡ MONKEY PATCH EN TOUT PREMIER - avant TOUT import
from gevent import monkey
monkey.patch_all()

import os
from app import app, socketio  # type: ignore

application = app
