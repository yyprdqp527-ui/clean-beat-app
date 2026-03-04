"""WSGI entry point for production (Gunicorn + eventlet + Flask-SocketIO)."""

try:
    # Import the Flask `app` and (optionally) `socketio` if present
    from app import app  # type: ignore
except Exception:
    # If import fails, provide a helpful error when the server tries to start
    raise

# Standard WSGI name expected by many servers
application = app

# If you want to expose the SocketIO server object too (some deployments
# may import it), try importing `socketio` from `app` and expose it here.
try:
    from app import socketio  # type: ignore
except Exception:
    socketio = None
