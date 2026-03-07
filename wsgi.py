"""WSGI entry point for production (Gunicorn + gevent/eventlet + Flask-SocketIO)."""

try:
    from gevent import monkey as _gevent_monkey
    _gevent_monkey.patch_all()
except ImportError:
    try:
        import eventlet
        eventlet.monkey_patch()
    except ImportError:
        pass

import os
from app import app, socketio  # type: ignore

application = app
