# 🔧 Guide de Dépannage - CleanBeat

## ✅ État Actuel

**Serveur** : ✅ Actif sur `http://192.168.1.156:8000`  
**Performance** : ✅ Chargement en ~0.06s  
**API Points** : ✅ Fonctionne (mise à jour toutes les 10s)

## 🌐 Accès à l'Application

### Sur le même réseau WiFi
- **Ordinateur/Tablette** : `http://192.168.1.156:8000`
- **Mobile** : `http://192.168.1.156:8000`

### En local (sur la machine serveur)
- `http://127.0.0.1:8000`
- `http://localhost:8000`

## 🐛 Problèmes Courants et Solutions

### 1. "La page ne se charge pas"

#### Cause A : Pas sur le même réseau WiFi
**Solution :**
- Vérifiez que tous les appareils sont sur le même WiFi
- Le serveur et l'appareil client doivent être sur le même réseau

#### Cause B : Serveur arrêté
**Vérification :**
```bash
lsof -i:8000 | grep LISTEN
```

**Si aucun résultat, relancer :**
```bash
cd "/Users/anne-gaelledaval/Downloads/Appli web-2"
python3 app.py
```

#### Cause C : Cache du navigateur
**Solution :**
1. Sur mobile : Vider le cache de Safari/Chrome
2. Sur desktop : Ctrl+F5 (ou Cmd+Shift+R sur Mac)
3. Mode navigation privée pour tester

### 2. "Les pages sont lentes"

**Optimisations appliquées :**
- ✅ Logs de debug supprimés
- ✅ Polling optimisé à 10 secondes
- ✅ Requêtes API légères

**Si encore lent :**
1. Vérifier la connexion WiFi
2. Redémarrer le serveur
3. Vider le cache navigateur

### 3. "Les points ne se mettent pas à jour"

**Vérifications :**
1. Attendez 10 secondes (intervalle normal)
2. Vérifiez la console navigateur (F12)
3. Vérifiez que vous êtes dans une maison

**Test manuel :**
```javascript
// Dans la console du navigateur
fetch('/api/players_points')
  .then(r => r.json())
  .then(d => console.log(d))
```

### 4. "Erreur 404 ou 500"

**Vérifier les logs serveur :**
- Regardez le terminal où tourne `python3 app.py`
- Notez l'erreur exacte

**Actions :**
1. Redémarrer le serveur
2. Vérifier que tous les fichiers sont présents
3. Vérifier la base de données `users.db`

### 5. "Déconnexion fréquente"

**Solutions :**
1. Ne pas utiliser plusieurs onglets avec le même compte
2. Vider les cookies
3. Se reconnecter

## 🔍 Commandes de Diagnostic

### Tester si le serveur répond
```bash
curl http://127.0.0.1:8000/ping
# Doit retourner: OK
```

### Tester l'API des points
```bash
curl http://127.0.0.1:8000/api/players_points
# Doit retourner du JSON avec les joueurs
```

### Voir les processus Python
```bash
ps aux | grep python3 | grep app.py
```

### Tuer le serveur si bloqué
```bash
lsof -ti:8000 | xargs kill -9
```

## 📱 Navigation Optimale

### Sur Mobile
1. Ajoutez l'app à l'écran d'accueil
2. Utilisez en plein écran
3. Gardez le WiFi actif

### Sur Desktop
1. Marquez la page en favori
2. Utilisez Chrome ou Safari (pas IE)
3. Gardez un seul onglet ouvert

## ⚡ Performances

### Temps de Chargement Normaux
- Page menu : **< 0.1s**
- Page catégorie : **< 0.2s**
- API points : **< 0.05s**

### Si Plus Lent
1. Vérifiez votre connexion WiFi
2. Redémarrez le serveur
3. Videz le cache

## 🔄 Redémarrage Rapide

```bash
# Arrêter
lsof -ti:8000 | xargs kill -9

# Démarrer
cd "/Users/anne-gaelledaval/Downloads/Appli web-2"
python3 app.py
```

Ou utilisez la tâche VS Code : "Lancer CleanBeat"

## 📊 Logs et Debug

### Activer les Logs (si besoin)
Les logs de debug ont été **désactivés** pour améliorer les performances.

Pour les réactiver temporairement, ajoutez dans la console :
```javascript
// Voir les requêtes API
fetch('/api/players_points')
  .then(r => r.json())
  .then(data => console.log('Points:', data))
```

## ✅ Checklist de Dépannage

Avant de demander de l'aide, vérifiez :

- [ ] Serveur actif (`lsof -i:8000`)
- [ ] Même réseau WiFi
- [ ] Cache navigateur vidé
- [ ] URL correcte (`192.168.1.156:8000`)
- [ ] Connecté avec un compte valide
- [ ] Dans une maison
- [ ] Pas d'erreurs dans les logs serveur

## 🆘 Problème Persistant ?

**Informations à fournir :**
1. Message d'erreur exact (capture d'écran)
2. URL que vous utilisez
3. Appareil (mobile/desktop, navigateur)
4. Logs du serveur (terminal)
5. Console du navigateur (F12)

## 🎯 Rappels Importants

- **Polling** : Les points se mettent à jour **toutes les 10 secondes**
- **Performance** : Optimisée pour mobile et desktop
- **Cache** : Videz-le si changements non visibles
- **WiFi** : Tous les appareils sur le même réseau

---

**Version** : 2.0 - Optimisée (logs debug supprimés)  
**Date** : 22 janvier 2026
