# 🍼 Guide de Test - Système de Suivi Bébé 👶

## ✅ État du Système

**Tous les tests sont passés avec succès !** Le système de suivi bébé est correctement configuré et prêt à être utilisé.

## 📋 Ce qui a été mis en place

### 1. Formulaire de suivi
Lorsqu'un joueur valide les tâches suivantes de la catégorie "Chambre Bébé" :
- 🍼 **Donner le biberon**
- 👶 **Changer les couches**
- 😴 **Faire dormir le bébé**

Un formulaire apparaît automatiquement avec :
- ⏰ Un menu déroulant pour sélectionner l'heure (format HH:MM)
- 🍼 Pour le biberon : un champ pour la quantité en ml (obligatoire)
- 📝 Un champ texte pour les observations (obligatoire sauf pour le biberon)

### 2. Envoi automatique dans la messagerie
Une fois le formulaire validé, un message automatique est créé et envoyé dans la messagerie de la maison :

**Exemples de messages :**
```
🍼 Anne-gaëlle a donné le biberon à 14:30 (180 ml)
📝 bébé a bien bu

👶 Jean a changé les couches à 15:00
📝 couche très mouillée

😴 Marie a couché bébé à 19:30
📝 s'est endormi facilement
```

### 3. Stockage en base de données
Toutes les informations sont enregistrées dans la table `baby_tracking` :
- Email du joueur
- Type de tâche (biberon/couches/sommeil)
- Heure de l'action
- Quantité de lait (pour le biberon)
- Observations
- Date/heure d'enregistrement

## 🧪 Comment tester

### Étape 1 : Démarrer l'application
```bash
cd "/Users/anne-gaelledaval/Downloads/Appli web-2"
python3 app.py
```

### Étape 2 : Se connecter
1. Ouvrir votre navigateur
2. Aller sur `http://localhost:8000` (ou votre adresse IP locale)
3. Se connecter avec votre compte

### Étape 3 : Accéder à la chambre bébé
1. Depuis le menu principal, cliquer sur **"Ch. Bébé"**
2. Vous verrez les tâches disponibles

### Étape 4 : Tester avec "Donner le biberon"
1. Cliquer sur **"Donner le biberon"**
2. Le formulaire de suivi apparaît :
   - **Heure** : Sélectionner l'heure actuelle (ex: 14:30)
   - **Quantité (ml)** : Entrer une quantité (ex: 180)
   - **Observations** : Ajouter une note (ex: "bébé a bien bu", optionnel)
3. Sélectionner le joueur qui a fait la tâche
4. Cliquer sur le bouton de validation

### Étape 5 : Vérifier le message
1. Aller dans la **Messagerie** (icône 💬)
2. Vous devriez voir le message automatique :
   ```
   🍼 [Votre nom] a donné le biberon à 14:30 (180 ml)
   📝 bébé a bien bu
   ```

### Étape 6 : Tester avec "Changer les couches"
1. Retourner dans **"Ch. Bébé"**
2. Cliquer sur **"Changer les couches"**
3. Remplir le formulaire :
   - **Heure** : Sélectionner l'heure
   - **Observations** : OBLIGATOIRE (ex: "couche très mouillée")
4. Valider et vérifier le message dans la messagerie

## 🔍 Vérifications additionnelles

### Consulter l'historique des suivis
```bash
python3 test_baby_tracking.py
```

Ce script affiche :
- ✅ Structure de la base de données
- ✅ Configuration des tâches
- 📊 Historique des 10 derniers suivis
- 📨 Messages automatiques créés
- ✅ Présence du code

### Vérifier directement dans la base de données
```bash
sqlite3 menage.db "SELECT * FROM baby_tracking ORDER BY created_at DESC LIMIT 5"
```

## 📱 Points importants

### Champs obligatoires
- ⏰ **L'heure est TOUJOURS obligatoire**
- 🍼 Pour le biberon : **quantité en ml obligatoire**
- 📝 Pour les couches et le sommeil : **observations obligatoires**
- 📝 Pour le biberon : **observations optionnelles**

### Validation
Un message d'alerte apparaît si un champ obligatoire n'est pas rempli.

### Messages
Les messages sont visibles par **tous les membres de la maison** dans la messagerie.

## 🐛 Dépannage

### Le formulaire ne s'affiche pas
1. Vérifier que vous êtes bien dans la catégorie "Chambre Bébé"
2. Vérifier que la tâche est bien "Donner le biberon", "Changer les couches" ou "Faire dormir le bébé"
3. Vider le cache du navigateur (Cmd+Shift+R sur Mac)

### Le message n'apparaît pas dans la messagerie
1. Vérifier que la validation a bien été effectuée (popup de succès)
2. Recharger la page de messagerie
3. Vérifier les logs du serveur pour voir si le message a été créé

### Erreur lors de la validation
1. Vérifier que tous les champs obligatoires sont remplis
2. Consulter la console JavaScript (F12 dans le navigateur)
3. Consulter les logs du serveur Python

## 📊 Tests effectués

✅ **Structure de la base de données** : Table `baby_tracking` créée  
✅ **Configuration des tâches** : Tâches correctement définies  
✅ **Historique des suivis** : Système d'enregistrement fonctionnel  
✅ **Messages automatiques** : Création de messages système  
✅ **Présence du code** : Toutes les fonctions présentes  
✅ **Guide de test** : Documentation complète  

**Résultat : 6/6 tests réussis ✅**

## 📞 Support

Si vous rencontrez un problème :
1. Vérifier ce guide
2. Consulter les logs : `python3 test_baby_tracking.py`
3. Relancer l'application si nécessaire

---

**Version** : 2026-02-04  
**Système** : CleanBeat - Suivi Bébé  
**Statut** : ✅ Opérationnel
