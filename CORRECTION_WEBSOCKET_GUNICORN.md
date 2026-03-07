# 🔧 Correction de l'erreur WebSocket - Résumé

## 🐛 Problème initial
```
[2026-03-07 22:58:01 +0000] [62] [ERROR] Error handling request /socket.io/?EIO=4&transport=websocket
```

Cette erreur indiquait que gunicorn avec le worker gevent ne pouvait pas gérer correctement les connexions WebSocket de Flask-SocketIO.

---

## ✅ Corrections appliquées

### 1. **wsgi.py** - Fix principal
**Problème:** Le fichier WSGI exposait directement l'objet Flask `app`, ce qui ne permettait pas à gunicorn de router correctement les requêtes WebSocket vers Flask-SocketIO.

**Solution:** Créer une fonction wrapper WSGI qui délègue les requêtes à `socketio` plutôt qu'à `app` directement.

```python
# AVANT
from app import app, socketio
application = app

# APRÈS
from app import app, socketio, SOCKETIO_AVAILABLE

if SOCKETIO_AVAILABLE and socketio:
    def application(environ, start_response):
        """WSGI application wrapper for Flask-SocketIO."""
        return socketio(environ, start_response)
else:
    application = app
```

**Impact:** Permet à gunicorn de router correctement les requêtes `/socket.io/*` vers le gestionnaire WebSocket de Flask-SocketIO.

---

### 2. **app.py** - Optimisation de la configuration SocketIO

**Changements:**
- Réduction des timeouts ping (120s → 60s) et ping interval (60s → 25s)
- Ajout d'options engineio pour meilleure gestion des buffers
- Configuration explicite des transports (websocket en priorité, polling en fallback)

```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
    ping_timeout=60,      # Réduit pour détecter plus vite les déconnexions
    ping_interval=25,     # Réduit pour maintenir la connexion active
    async_mode=_async_mode,
    engineio_options={
        'max_http_buffer_size': 1000000,  # 1MB buffer
        'transports': ['websocket', 'polling'],
    }
)
```

**Impact:** 
- Meilleure réactivité de détection des déconnexions
- Moins de risque de timeout sur connexions lentes
- Configuration explicite des transports évite les problèmes d'auto-négociation

---

### 3. **gunicorn_config.py** - Amélioration du logging

**Changements:**
- Niveau de log passé de `warning` à `info` pour voir les erreurs WebSocket
- Ajout de `worker_connections = 1000` pour limiter les connexions par worker

```python
loglevel = 'info'  # Au lieu de 'warning'
worker_connections = 1000
```

**Impact:** 
- Meilleur suivi des erreurs WebSocket dans les logs
- Protection contre la surcharge du worker

---

## 🔍 Tests de validation

Un script de test a été créé : `test_websocket_connection.py`

**Usage:**
```bash
python3 test_websocket_connection.py
```

**Vérifie:**
1. ✅ Toutes les dépendances nécessaires (Flask, Flask-SocketIO, gevent, etc.)
2. ✅ Import correct de l'application avec SocketIO configuré
3. ✅ Module WSGI exposé correctement
4. ✅ Gestionnaires SocketIO enregistrés (connect, disconnect, join_house, etc.)
5. ✅ Configuration actuelle

---

## 🚀 Déploiement sur Render

La configuration est maintenant prête pour Render :

1. **Commande de build:** `pip install -r requirements.txt`
2. **Commande de start:** `gunicorn -c gunicorn_config.py wsgi:application`
3. **Worker:** gevent (défini dans gunicorn_config.py)
4. **Port:** Automatiquement détecté via `$PORT`

---

## 🎯 Pourquoi ça fonctionne maintenant

### Avec gunicorn + gevent + Flask-SocketIO:

1. **Gunicorn** charge le module `wsgi.py` et appelle `application(environ, start_response)`
2. **Notre wrapper WSGI** délègue l'appel à `socketio(environ, start_response)`
3. **Flask-SocketIO** examine la requête:
   - Si c'est une requête `/socket.io/*` → gère via le protocole WebSocket/Engine.IO
   - Si c'est une requête HTTP normale → délègue à l'app Flask standard
4. **gevent worker** gère les connexions asynchrones avec monkey patching

### Configuration cohérente:

- En **production (Render):** `async_mode='gevent'` + worker gevent → WebSockets performants
- En **développement (local):** `async_mode='threading'` → Facile à déboguer

---

## 📊 Architecture après les corrections

```
[Client Browser]
     ↓
[Connexion WebSocket: /socket.io/?EIO=4&transport=websocket]
     ↓
[Render Load Balancer]
     ↓
[Gunicorn avec worker gevent]
     ↓
[wsgi.py: application(environ, start_response)]
     ↓
[socketio(environ, start_response)]  ← FIX PRINCIPAL
     ↓
├─ Si /socket.io/* → [Flask-SocketIO Engine.IO/WebSocket Handler]
│                     ↓
│                    [Gestionnaires @socketio.on('connect'), etc.]
│
└─ Sinon → [Flask App Routes]
           ↓
          [Routes Flask normales: /, /menu, /tasks, etc.]
```

---

## 🔧 Si l'erreur persiste sur Render

1. **Vérifier les logs Render:**
   ```bash
   # Chercher dans les logs:
   - "WebSocket activé pour la synchronisation en temps réel"
   - "async_mode = gevent"
   - Erreurs contenant "socket.io"
   ```

2. **Vérifier la connexion client:**
   - Ouvrir DevTools → Network
   - Chercher la requête `/socket.io/?EIO=4&transport=websocket`
   - Status devrait être `101 Switching Protocols`

3. **Activer les logs SocketIO temporairement:**
   Dans app.py, changer:
   ```python
   socketio = SocketIO(
       app,
       logger=True,        # Activer temporairement
       engineio_logger=True,  # Activer temporairement
       ...
   )
   ```

4. **Vérifier que gevent est bien installé sur Render:**
   Dans les logs de build, chercher:
   ```
   Successfully installed gevent-24.2.1
   Successfully installed gevent-websocket-0.10.1
   Successfully installed flask-socketio-5.3.6
   ```

---

## 📝 Fichiers modifiés

1. ✅ `wsgi.py` - Wrapper WSGI pour Flask-SocketIO
2. ✅ `app.py` - Configuration SocketIO optimisée
3. ✅ `gunicorn_config.py` - Logging et connexions améliorés
4. ✅ `test_websocket_connection.py` - Script de validation (nouveau)
5. ✅ `CORRECTION_WEBSOCKET_GUNICORN.md` - Cette documentation

---

## 🎉 Résultat attendu

Après déploiement sur Render avec ces corrections:

- ✅ Les connexions WebSocket fonctionnent sans erreur
- ✅ Les clients peuvent se connecter via `/socket.io/`
- ✅ Les événements temps réel sont diffusés correctement
- ✅ Pas d'erreur "Error handling request /socket.io/" dans les logs
- ✅ Status HTTP 101 (Switching Protocols) pour les upgrades WebSocket

---

**Date de correction:** 8 mars 2026  
**Version Flask-SocketIO:** 5.3.6+  
**Version Gunicorn:** 21.2.0+  
**Worker:** gevent
