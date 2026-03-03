"""WSGI entry point for production servers.

This file exposes a WSGI callable named `application` so servers
like Gunicorn, uWSGI or Waitress can import and serve the Flask app.

Usage examples (from project root):
  - Gunicorn (HTTP only):
      pip install gunicorn
      gunicorn -w 4 -b 0.0.0.0:8000 wsgi:application

  - Gunicorn + eventlet (if you use Flask-SocketIO):
      pip install gunicorn eventlet
      gunicorn -k eventlet -w 1 -b 0.0.0.0:8000 wsgi:application

  - Waitress (Windows-friendly):
      pip install waitress
      waitress-serve --listen=*:8000 wsgi:application

Adjust worker count and bind address to your environment and load.
"""

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
