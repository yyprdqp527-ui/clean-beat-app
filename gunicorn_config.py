"""Configuration Gunicorn pour CleanBeat sur Render avec gevent."""

# ⚡ MONKEY PATCH EN TOUT PREMIER - avant même l'import de app
from gevent import monkey
monkey.patch_all()
try:
    from psycogreen.gevent import patch_psycopg; patch_psycopg()
except ImportError:
    pass

import multiprocessing
import os

# Worker class - DOIT être gevent pour Flask-SocketIO
worker_class = 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker'

# Nombre de workers — 2 sur Render Starter pour paralléliser les requêtes simultanées
# (gevent gère de nombreuses connexions par worker via async I/O)
workers = 2

# Threads par worker (pas utilisé avec gevent mais défini pour clarté)
threads = 1

# Timeout pour les connexions WebSocket persistantes
timeout = 30
graceful_timeout = 120
keepalive = 5

# Bind address (Render définit le PORT)
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'  # Changé de 'warning' à 'info' pour voir les erreurs WebSocket

# Préchargement de l'app (plus rapide au démarrage)
preload_app = False  # False pour éviter les problèmes de monkey patching

# Max requests avant restart worker (évite les fuites mémoire)
max_requests = 1000
max_requests_jitter = 100

# Options supplémentaires pour WebSocket
worker_connections = 200   # Augmenté pour tirer parti du single worker gevent
