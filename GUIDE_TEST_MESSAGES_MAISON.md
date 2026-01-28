# 🚀 Guide de Test - Système de Messages de la Maison

## Test rapide (5 minutes)

### 1. Vérifier que l'application tourne
L'application devrait être lancée sur `http://localhost:8000`

### 2. Se connecter
- Connectez-vous avec votre compte (ex: agdaval@yahoo.fr / Marinette)

### 3. Tester les messages manuellement

#### Option A : Via les URLs de test

**Encouragement personnalisé :**
```
http://localhost:8000/test_house_encouragement
```
→ La maison t'envoie un message d'encouragement avec ton nom

**Sermon humoristique :**
```
http://localhost:8000/test_house_sermon
```
→ La maison te taquine gentiment

**Sermon général (inactivité) :**
```
http://localhost:8000/test_house_sermon_lazy
```
→ Message général humoristique sur l'inactivité

#### Option B : Via la console Python

```python
# Ouvrir un terminal Python
python3

# Importer les fonctions
import sqlite3
import sys
sys.path.append('/Users/anne-gaelledaval/Downloads/Appli web-2')
from app import send_house_encouragement, send_house_sermon

# ID de la maison Biscotte
house_id = 149

# Envoyer un encouragement
send_house_encouragement(house_id, player_name="Marinette")

# Envoyer un sermon humoristique
send_house_sermon(house_id, player_name="Jean-marie", sermon_type='funny')

# Envoyer un sermon général
send_house_sermon(house_id, sermon_type='lazy')
```

### 4. Voir les messages dans la messagerie

1. Aller sur `http://localhost:8000/comments`
2. Tu devrais voir les messages de la maison 🏠
3. Ils apparaissent avec :
   - Un grand avatar de maison 🏠
   - Une bulle dorée
   - Le nom "🏠 Biscotte"

### 5. Vérifier les notifications push

Si tu as activé les notifications :
- Tu recevras une notification push
- Titre : "🏠 Biscotte"
- Corps : Le message
- Cliquer dessus ouvre `/comments`

## Test avec plusieurs joueurs

1. Ouvre plusieurs navigateurs (ou fenêtres incognito)
2. Connecte différents joueurs de la maison :
   - agdaval@yahoo.fr (Marinette)
   - baconjean@hotmail.com (Jean-marie)
   - maryline@hotmail.com (Jocelyne)
3. Envoie un message via une des URLs de test
4. Tous les joueurs reçoivent le message dans `/comments`

## Exemples de messages que tu verras

### Encouragements 💪
- "🎉 Bravo Marinette ! Tu cartonnes aujourd'hui !"
- "✨ Super boulot Marinette ! La maison brille grâce à toi !"
- "🌟 Marinette, tu es au top ! Continue comme ça !"

### Sermons humoristiques 😄
- "🏠 Jean-marie, tu te caches ou quoi ? Ça fait un bail ! 🕵️"
- "🏠 Marinette, même les plantes en font plus que toi ! Et elles bougent pas ! 🪴😂"
- "🏠 Jocelyne, tu joues à cache-cache avec le ménage ? Tu gagnes ! 🙈"

### Sermons généraux 😅
- "🏠 Euh... je ne veux pas être désagréable mais... ça fait 3 jours que personne ne fait rien ! 😅"
- "🏠 Les amis, je commence à ressembler à une maison hantée... Un petit coup de balai ? 👻"
- "🏠 SOS ! La vaisselle sale prépare une révolution ! Qui vient négocier ? 🍽️"

## Vérification dans la base de données

```bash
# Ouvrir la base de données
sqlite3 users.db

# Voir les messages de la maison
SELECT sender_email, content, message_type, timestamp 
FROM messages 
WHERE house_id=149 AND sender_type='house' 
ORDER BY timestamp DESC 
LIMIT 10;

# Compter les messages
SELECT COUNT(*) FROM messages WHERE house_id=149 AND sender_type='house';

# Quitter
.quit
```

## Résolution de problèmes

### Pas de messages ?
- Vérifier que l'application tourne sur le port 8000
- Vérifier que tu es connecté
- Vérifier la console pour les erreurs Python

### Messages pas visibles dans /comments ?
- Rafraîchir la page (F5)
- Vérifier les logs du serveur
- Vérifier la base de données (requête SQL ci-dessus)

### Pas de notifications push ?
- Vérifier que les notifications sont activées dans le navigateur
- Regarder la console JavaScript (F12)

## Prochains tests

1. **Test automatique d'activité**
   - Laisser la maison sans activité pendant 3 jours
   - La fonction `check_house_activity_and_send_message()` devrait envoyer un sermon

2. **Test après tâches**
   - Compléter plusieurs tâches
   - La maison devrait féliciter automatiquement

3. **Test personnalisation**
   - Modifier les messages dans HOUSE_MESSAGES
   - Redémarrer l'app
   - Tester les nouveaux messages

---

**Astuce** : Les URLs de test sont parfaites pour le développement. En production, les messages seront envoyés automatiquement selon l'activité ! 🎮✨
