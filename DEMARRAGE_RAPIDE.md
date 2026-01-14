# 🚀 DÉMARRAGE RAPIDE - Système d'Invitation CleanBeat

## ⚡ Test en 5 minutes

### 1️⃣ Lancer l'application

```bash
cd "/Users/anne-gaelledaval/Downloads/Appli web-2"
python3 app.py
```

L'application démarre sur **http://127.0.0.1:8000**

### 2️⃣ Accéder à la page de test

Ouvrez votre navigateur : **http://127.0.0.1:8000/test_invitation**

Cette page contient :
- 📖 Explications détaillées
- 🔗 Liens directs vers chaque fonctionnalité
- 🧪 Cas de test recommandés
- 📝 Données de test prêtes

### 3️⃣ Tester l'invitation (Hôte)

1. **Créer un compte si nécessaire**
   - Aller sur `/signup` ou `/register`
   - Créer votre compte hôte

2. **Inviter des partenaires**
   - Aller sur `/invite_partner`
   - Noter votre **code de maison** (exemple : `ABC123`)
   - Ajouter des partenaires :
     - Nom : `Marie`
     - Téléphone : `+33 6 12 34 56 78`
   - Cliquer sur "➕ Ajouter à la liste"
   - Ajouter d'autres partenaires si besoin
   - Cliquer sur "📱 Envoyer les invitations SMS"

3. **Vérifier**
   - Message de confirmation s'affiche
   - Dans la console du serveur, vous verrez les SMS simulés

### 4️⃣ Tester la rejointe (Partenaire)

1. **Accéder à la page**
   - Aller sur `/join_house`

2. **Étape 1 : Code**
   - Entrer le code noté précédemment (ex: `ABC123`)
   - Cliquer "Suivant"

3. **Étape 2 : Nom de maison**
   - Entrer : `Notre petit nid`
   - Cliquer "Suivant"

4. **Étape 3 : Compte**
   - Nom : `Marie`
   - Email : `marie@test.com`
   - Mot de passe : `password123`
   - Cliquer "Suivant"

5. **Étape 4 : Confirmation**
   - Vérifier le récapitulatif
   - Cliquer "🚀 Rejoindre et commencer à jouer !"

6. **Résultat**
   - ✅ Connexion automatique
   - ✅ Redirection vers le menu
   - ✅ Message de bienvenue
   - ✅ Marie est maintenant dans la maison !

## 📱 URLs Rapides

| Page | URL | Description |
|------|-----|-------------|
| 🧪 **Test** | `/test_invitation` | Page de test complète |
| 💌 **Inviter** | `/invite_partner` | Inviter des partenaires (Hôte) |
| 🏠 **Rejoindre** | `/join_house` | Rejoindre une maison (Partenaire) |
| 🔐 **Connexion** | `/login` | Se connecter |
| 📝 **Inscription** | `/signup` | Créer un compte |
| 🎮 **Menu** | `/menu` | Menu principal du jeu |

## 🎯 Scénario complet de A à Z

### Partie 1 : L'Hôte (Paul)
1. Paul crée un compte sur CleanBeat
2. Il crée sa maison "Villa des Champions"
3. Il va sur `/invite_partner`
4. Son code de maison : `XYZ789`
5. Il invite Marie (`+33 6 12 34 56 78`)
6. Il invite Thomas (`+33 6 87 65 43 21`)
7. Il clique "Envoyer les invitations"
8. ✅ 2 SMS envoyés (simulés)

### Partie 2 : Le Partenaire (Marie)
1. Marie reçoit le SMS avec le code `XYZ789`
2. Elle clique sur le lien `/join_house`
3. **Étape 1** : Elle entre `XYZ789`
4. **Étape 2** : Elle nomme la maison "Notre Cocon"
5. **Étape 3** : Elle crée son compte
   - Nom : `Marie`
   - Email : `marie@example.com`
   - Mot de passe : `marie2025`
6. **Étape 4** : Elle valide le récapitulatif
7. ✅ Elle est connectée automatiquement
8. ✅ Elle voit le menu de la maison
9. ✅ Elle peut jouer avec Paul !

### Partie 3 : Autre Partenaire (Thomas)
1. Thomas reçoit aussi le SMS
2. Il fait la même chose que Marie
3. Maintenant il y a 3 joueurs dans la maison !

## 🐛 Dépannage rapide

### Problème : "Port déjà utilisé"
```bash
lsof -ti:8000 | xargs kill -9
python3 app.py
```

### Problème : "Code invalide"
- Vérifier que le code est en MAJUSCULES
- Vérifier qu'il fait bien 6 caractères
- Demander à l'hôte de vérifier son code

### Problème : "Email déjà utilisé"
- Utiliser un autre email
- Ou se connecter avec cet email

### Problème : Page blanche
- Vérifier que l'app est lancée
- Vérifier l'URL (port 8000)
- Regarder la console du serveur

## 📚 Documentation

- **Guide utilisateur** : `GUIDE_INVITATION.md`
- **Documentation technique** : `FLUX_INVITATION.md`
- **Résumé des modifications** : `RESUME_MODIFICATIONS_INVITATION.md`

## ✨ Fonctionnalités principales

✅ **Invitation multiple** : Inviter plusieurs personnes à la fois
✅ **Processus guidé** : 4 étapes claires pour rejoindre
✅ **Validation intelligente** : Erreurs claires et utiles
✅ **Responsive** : Fonctionne sur mobile et desktop
✅ **Moderne** : Interface belle et intuitive
✅ **Sécurisé** : Mots de passe hashés, validations
✅ **Automatique** : Connexion auto après inscription

## 🎉 C'est parti !

Vous avez maintenant tout ce qu'il faut pour tester le système d'invitation CleanBeat !

**Bonne chance et amusez-vous bien ! 🎮**

---

💡 **Astuce** : Commencez par la page de test pour avoir une vue d'ensemble complète.

🔗 **Accès direct** : http://127.0.0.1:8000/test_invitation
