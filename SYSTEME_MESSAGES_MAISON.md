# 🏠 Système de Messages de la Maison - CleanBeat

## Vue d'ensemble

La maison "Biscotte" peut maintenant communiquer avec les joueurs via la messagerie ! Elle possède :
- **Un avatar** : 🏠 (icône de maison)
- **Une personnalité humoristique** qui encourage et sermonne les joueurs
- **Des messages automatiques** basés sur l'activité

## Types de messages

### 1. 💪 Messages d'encouragement
La maison félicite et encourage les joueurs actifs :
- "🎉 Bravo {name} ! Tu cartonnes aujourd'hui !"
- "✨ Super boulot {name} ! La maison brille grâce à toi !"
- "💪 {name}, tu assures grave ! Respect !"

**Quand ?** Quand un joueur complète plusieurs tâches ou quand l'activité est élevée.

### 2. 😄 Sermons humoristiques (personnalisés)
La maison taquine gentiment un joueur inactif :
- "🏠 {name}, tu te caches ou quoi ? Ça fait un bail ! 🕵️"
- "🏠 {name}, je t'ai vu passer mais tu as fait zéro tâche ! C'est une technique ninja ? 🥷"
- "🏠 {name}, tu attends que je fasse le ménage toute seule ? Spoiler : je sais pas ! 🤷"

**Quand ?** Pour rappeler à un joueur spécifique qu'il n'a pas été actif.

### 3. 😅 Sermons généraux (inactivité)
La maison fait de l'humour sur l'inactivité générale :
- "🏠 Euh... je ne veux pas être désagréable mais... ça fait 3 jours que personne ne fait rien ! 😅"
- "🏠 Les amis, je commence à ressembler à une maison hantée... Un petit coup de balai ? 👻"
- "🏠 SOS ! La vaisselle sale prépare une révolution ! Qui vient négocier ? 🍽️"

**Quand ?** Après 3 jours sans activité dans la maison.

## Fonctions disponibles

### En Python (app.py)

```python
# Envoyer un encouragement
send_house_encouragement(house_id, player_name="Marinette")

# Envoyer un sermon humoristique à un joueur
send_house_sermon(house_id, player_name="Jean-marie", sermon_type='funny')

# Envoyer un sermon général pour inactivité
send_house_sermon(house_id, sermon_type='lazy')

# Vérifier l'activité et envoyer un message automatique
check_house_activity_and_send_message(house_id)
```

### Routes de test (URL)

Pour tester le système manuellement :

1. **Test encouragement** : `http://localhost:8000/test_house_encouragement`
   - Envoie un message d'encouragement personnalisé avec ton nom

2. **Test sermon personnalisé** : `http://localhost:8000/test_house_sermon`
   - La maison te taquine gentiment

3. **Test sermon général** : `http://localhost:8000/test_house_sermon_lazy`
   - Message général sur l'inactivité

## Affichage dans la messagerie

Les messages de la maison apparaissent dans `/comments` avec :
- **Avatar** : Grande icône 🏠 (50px)
- **Nom** : "🏠 Biscotte" (ou le nom de votre maison)
- **Style** : Bulles dorées (#FDAE54) avec effet glassmorphisme
- **Position** : Centrés dans la conversation

## Intégration automatique

Le système peut être intégré pour envoyer des messages automatiquement :

### 1. Après une tâche complétée
```python
# Dans la route de validation de tâche
if nombre_de_taches_ce_jour > 5:
    send_house_encouragement(house_id, player_name=user_name)
```

### 2. Vérification quotidienne
Créer une tâche cron ou scheduler pour vérifier l'activité :
```python
# Tous les jours à 20h
check_house_activity_and_send_message(house_id)
```

### 3. Déclenchement manuel
Via un bouton dans l'interface admin ou le menu.

## Configuration

### Modifier les messages

Les messages sont définis dans `app.py` ligne ~2425 :
```python
HOUSE_MESSAGES = {
    'congratulation': [...],
    'encouragement': [...],
    'sermon_lazy': [...],
    'sermon_funny': [...]
}
```

### Modifier l'avatar de la maison

Dans `app.py`, fonction `send_house_encouragement()` :
```python
sender_name=f"🏠 {house_name}"  # Changer l'emoji ici
```

Dans `templates/comments.html`, ligne ~538 :
```html
<div class="message-avatar" style="font-size: 50px;">
    🏠  <!-- Changer l'emoji ici -->
</div>
```

## Base de données

Les messages sont stockés dans la table `messages` avec :
- `sender_type` = `'house'` (au lieu de 'user' ou 'system')
- `sender_email` = nom de la maison (ex: "🏠 Biscotte")
- `message_type` = `'sermon'`, `'encouragement'`, ou `'congratulation'`
- `house_id` = ID de la maison

## Notifications push

Les messages de la maison envoient également des notifications push avec :
- **Titre** : "🏠 Biscotte" (nom de la maison)
- **Corps** : Le contenu du message
- **Redirection** : Vers `/comments` pour voir le message

## Exemples d'utilisation

### Scénario 1 : Féliciter un joueur très actif
```python
# Après 10 tâches en une journée
send_house_encouragement(house_id, player_name="Marinette")
# → "🎉 Bravo Marinette ! Tu cartonnes aujourd'hui !"
```

### Scénario 2 : Rappeler gentiment un joueur inactif
```python
# Après 5 jours sans activité
send_house_sermon(house_id, player_name="James", sermon_type='funny')
# → "🏠 James, tu te caches ou quoi ? Ça fait un bail ! 🕵️"
```

### Scénario 3 : Motivation générale
```python
# Aucune tâche depuis 3 jours
send_house_sermon(house_id, sermon_type='lazy')
# → "🏠 Les copains, la poussière organise une fête chez moi... 🎉🧹"
```

## Personnalisation par maison

Chaque maison peut avoir :
- Son propre nom (ex: "Biscotte", "La Villa", "Chez nous")
- Des messages adaptés en fonction du `house_type` (couple, coloc, famille)
- Une fréquence différente de messages automatiques

## Prochaines étapes possibles

1. **Messages programmés** : Rappels hebdomadaires automatiques
2. **Réponses intelligentes** : La maison répond aux messages des joueurs
3. **Niveaux d'humeur** : La maison plus/moins joyeuse selon l'activité
4. **Achievements** : Messages spéciaux pour les jalons (100 tâches, etc.)
5. **Messages saisonniers** : Messages adaptés aux saisons/fêtes

---

**Note** : Le système respecte la personnalité ludique de CleanBeat tout en restant motivant et positif ! 🎮✨
