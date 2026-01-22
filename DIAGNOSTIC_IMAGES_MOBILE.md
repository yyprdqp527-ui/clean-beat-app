# 🔧 DIAGNOSTIC: Images ne se chargent pas sur mobile

## Problème identifié
Les images ne se chargent pas sur votre mobile (192.168.1.189) depuis le serveur CleanBeat.

## Tests effectués ✅

1. **Serveur accessible**: ✅ Le serveur répond sur http://192.168.1.156:8000
2. **Images accessibles depuis le serveur**: ✅ Les images répondent avec HTTP 200
3. **Permissions des fichiers**: ✅ Les fichiers ont les bonnes permissions (rw-r--r--)

## Causes probables

### 1. **Encodage des caractères spéciaux** (TRÈS PROBABLE)
Les noms de fichiers contiennent des caractères accentués et des espaces :
- `laver les sols.webp` (espaces)
- `éponger le sol.webp` (caractère é)
- `faire la poussière.webp` (è)
- `chambre bébé/` (é)

**Impact sur mobile**: Les navigateurs mobiles peuvent avoir du mal à encoder correctement ces URLs.

### 2. **Cache du navigateur mobile**
Le navigateur mobile peut avoir mis en cache des versions 404 des images.

### 3. **Taille des images**
Certaines images sont encore assez grandes :
- `Passer l'aspirateur.webp`: 135K
- Possibles timeouts sur connexion mobile lente

## Solutions proposées

### Solution 1: Page de test (DÉJÀ CRÉÉE) ⭐
**URL à tester sur votre mobile**: 
```
http://192.168.1.156:8000/test_images_mobile
```

Cette page va :
- Afficher plusieurs images avec différentes méthodes
- Tester l'encodage des URLs
- Montrer les erreurs de chargement
- Afficher des statistiques de connexion

**Action**: Ouvrez cette URL sur votre mobile et regardez quelles images se chargent et lesquelles échouent.

### Solution 2: Vider le cache du navigateur mobile
1. Sur Safari (iOS):
   - Réglages > Safari > Effacer historique et données de sites
2. Sur Chrome (Android):
   - Paramètres > Confidentialité > Effacer les données de navigation

### Solution 3: Optimiser les noms de fichiers (si nécessaire)
Si la page de test montre des erreurs d'encodage, nous devrons :
1. Renommer les fichiers pour supprimer les accents
2. Remplacer les espaces par des tirets ou underscores
3. Mettre à jour les références dans `app.py`

**Exemple**:
- `laver les sols.webp` → `laver-les-sols.webp`
- `éponger le sol.webp` → `eponger-le-sol.webp`

### Solution 4: Utiliser des URLs encodées
Modifier le template pour encoder automatiquement les URLs :

```python
{{ url_for('static', filename='images/' ~ task_image) | urlencode }}
```

## Prochaines étapes

### Étape 1: TEST IMMÉDIAT 🎯
**Sur votre mobile, ouvrez**:
```
http://192.168.1.156:8000/test_images_mobile
```

Cette page va diagnostiquer le problème exact.

### Étape 2: Analyser les résultats
- Si toutes les images se chargent ✅ → Le problème vient du template principal
- Si certaines images échouent ❌ → Problème d'encodage ou de cache
- Si aucune image ne se charge ❌ → Problème réseau ou de configuration

### Étape 3: Appliquer la solution appropriée
Selon les résultats du test, nous appliquerons la solution adaptée.

## Informations techniques

**Configuration serveur**:
- IP: 192.168.1.156
- Port: 8000
- Flask debug: ON
- Host: 0.0.0.0 (accessible depuis le réseau)

**Client mobile**:
- IP: 192.168.1.189
- Réseau: Même réseau local que le serveur ✅

**Images testées**:
- salon/laver les sols.webp: HTTP 200 ✅
- salon/faire la poussière.webp: Non testé
- salle de bain/éponger le sol.webp: Configuration vérifiée ✅

## Template actuel
Le template `task_page_enhanced.html` utilise :
```html
<img src="{{ url_for('static', filename='images/' ~ task_image) }}" alt="{{ task_name }}">
```

Cette méthode devrait encoder correctement les URLs, mais peut ne pas fonctionner sur tous les navigateurs mobiles.

## Commandes utiles

### Redémarrer le serveur:
```bash
cd "/Users/anne-gaelledaval/Downloads/Appli web-2"
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 2
python3 app.py &
```

### Tester l'accès aux images depuis le Mac:
```bash
curl -I "http://192.168.1.156:8000/static/images/salon/laver%20les%20sols.webp"
```

### Vérifier les logs du serveur:
```bash
tail -f server.log
```

## État actuel
- ✅ Serveur démarré sur http://192.168.1.156:8000
- ✅ Page de test créée: `/test_images_mobile`
- ✅ Route ajoutée dans app.py
- ⏳ EN ATTENTE: Test sur mobile par l'utilisateur

---

**Prochaine action**: Testez http://192.168.1.156:8000/test_images_mobile sur votre mobile et partagez les résultats.
