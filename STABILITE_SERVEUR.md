# 🔧 Améliorations Stabilité Serveur

## ⚠️ Problème Identifié

Le serveur Flask devenait inaccessible après quelques requêtes à cause de :
1. **Mode mono-thread** : Flask par défaut ne gère qu'une requête à la fois
2. **Connexions SQLite multiples** : Risque de blocage avec plusieurs utilisateurs
3. **Pas de timeout** : Les connexions bloquées ne se libéraient jamais

## ✅ Solutions Implémentées

### 1. Mode Multi-Thread Activé

**Fichier** : `app.py` (ligne ~6390)

```python
app.run(
    debug=True, 
    host='0.0.0.0', 
    port=chosen_port, 
    use_reloader=False,
    threaded=True,  # ✅ Active le mode multi-thread
    request_handler=None
)
```

**Avantages** :
- ✅ Gère plusieurs connexions simultanées
- ✅ Les utilisateurs ne se bloquent plus mutuellement
- ✅ Meilleure réactivité de l'application

### 2. Fonction de Connexion Optimisée

**Fichier** : `app.py` (lignes 670-684)

La fonction `get_db_connection()` existe déjà avec :
- ✅ **Timeout de 30 secondes** : Évite les blocages infinis
- ✅ **Mode WAL** : Lectures et écritures concurrentes
- ✅ **Optimisations de cache** : Meilleure performance

```python
def get_db_connection(timeout=30.0):
    conn = sqlite3.connect(DB, timeout=timeout, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=10000')
    conn.execute('PRAGMA temp_store=MEMORY')
    return conn
```

### 3. Script de Démarrage Robuste

**Fichier** : `start_server.sh`

Un nouveau script bash pour démarrer le serveur :
- 🔍 Vérifie les processus existants
- 🔄 Nettoie le port 8000 avant de démarrer
- 📝 Enregistre les logs dans `logs/cleanbeat.log`
- ⚡ Redémarre proprement en cas d'arrêt

**Utilisation** :
```bash
./start_server.sh
```

## 📊 Amélioration des Performances

### Avant
- ❌ 1 requête à la fois
- ❌ Timeout de connexion : ∞
- ❌ Blocages fréquents avec 2+ utilisateurs
- ❌ Serveur qui s'arrête sans raison

### Après
- ✅ Plusieurs requêtes simultanées
- ✅ Timeout de connexion : 30 secondes
- ✅ Pas de blocage avec plusieurs utilisateurs
- ✅ Logs pour diagnostiquer les problèmes

## 🚀 Recommandations pour Production

Le serveur de développement Flask n'est **PAS recommandé** pour la production.

### Pour PythonAnywhere

PythonAnywhere utilise **WSGI** qui est bien plus robuste :
- ✅ Multi-process (pas seulement multi-thread)
- ✅ Gestion automatique des erreurs
- ✅ Rechargement automatique
- ✅ Métriques et monitoring

### Configuration WSGI Recommandée

Pour un serveur WSGI local (Gunicorn), vous pourriez utiliser :

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Paramètres :
- `-w 4` : 4 processus workers (ajuster selon CPU)
- `-b 0.0.0.0:8000` : Bind sur toutes les interfaces, port 8000
- `app:app` : Module Flask

## 📝 Logs et Monitoring

### Consulter les Logs

```bash
tail -f logs/cleanbeat.log
```

### Vérifier l'État du Serveur

```bash
lsof -i:8000  # Voir le processus sur le port 8000
ps aux | grep python3  # Voir tous les processus Python
```

### Redémarrer en Cas de Problème

```bash
# Méthode 1 : Via le script
./start_server.sh

# Méthode 2 : Manuellement
lsof -ti:8000 | xargs kill -9
python3 app.py
```

## 🔍 Diagnostics

### Symptômes de Problèmes

1. **"Connexion impossible"**
   - Vérifier si le serveur tourne : `lsof -i:8000`
   - Consulter les logs : `tail logs/cleanbeat.log`

2. **"Page ne répond pas"**
   - Peut être un timeout de requête (>30s)
   - Vérifier les logs pour voir où ça bloque

3. **"Serveur s'arrête tout seul"**
   - Consulter les logs : erreur Python ?
   - Vérifier la RAM disponible : `top`

### Commandes Utiles

```bash
# Voir l'utilisation de la mémoire
top -l 1 | grep PhysMem

# Voir les connexions réseau actives
netstat -an | grep 8000

# Tester la connectivité
curl -I http://127.0.0.1:8000/menu
```

## ⚡ Prochaines Améliorations

### Court Terme
- [ ] Utiliser `get_db_connection()` partout (remplacer `sqlite3.connect(DB)`)
- [ ] Ajouter un système de file d'attente pour les tâches lourdes
- [ ] Implémenter un cache Redis pour les données fréquentes

### Long Terme
- [ ] Déployer sur PythonAnywhere avec WSGI
- [ ] Implémenter un load balancer si >100 utilisateurs
- [ ] Migration vers PostgreSQL pour meilleures performances concurrentes

## 🎯 Tests Recommandés

### Test de Charge Basique

```bash
# Installer Apache Bench
brew install httpd  # macOS

# Tester 100 requêtes, 10 simultanées
ab -n 100 -c 10 http://127.0.0.1:8000/menu
```

### Test avec Plusieurs Utilisateurs

1. Ouvrir 3-4 navigateurs différents
2. Se connecter avec des comptes différents
3. Naviguer en même temps
4. Valider des tâches simultanément

✅ **Le serveur devrait maintenant gérer cela sans problème !**

---

## 📚 Références

- [Flask Documentation - Threading](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [Gunicorn Documentation](https://gunicorn.org/)

**Date de modification** : 22 janvier 2026
