# 🎉 Guide d'Utilisation - Système d'Invitation CleanBeat

## 📱 Comment inviter des partenaires ?

### Étape 1 : Accéder à la page d'invitation

1. Connectez-vous à votre compte CleanBeat
2. Allez sur la page `/invite_partner`
3. Vous verrez votre **code de maison** affiché en haut

### Étape 2 : Ajouter des partenaires

1. **Entrez le nom** de votre partenaire
2. **Entrez son numéro de téléphone** (format : +33 6 XX XX XX XX)
3. Cliquez sur **"➕ Ajouter à la liste"**
4. Répétez pour ajouter d'autres partenaires

### Étape 3 : Envoyer les invitations

1. Vérifiez la liste des partenaires
2. Cliquez sur **"📱 Envoyer les invitations SMS"**
3. Un SMS sera envoyé à chaque partenaire avec :
   - Votre nom
   - Le code de la maison
   - Le lien pour rejoindre

## 🏠 Comment rejoindre une maison ?

### Pour les partenaires invités :

1. **Accédez au lien** reçu par SMS : `/join_house`

2. **Étape 1 - Code de la maison**
   - Entrez le code à 6 caractères reçu par SMS
   - Exemple : `ABC123`
   - Cliquez sur "Suivant"

3. **Étape 2 - Nom de la maison**
   - Donnez un nom sympa à votre maison
   - Exemples : "Chez nous", "La villa du bonheur"
   - Cliquez sur "Suivant"

4. **Étape 3 - Créer votre compte**
   - Entrez votre nom
   - Entrez votre email (unique)
   - Créez un mot de passe (min 6 caractères)
   - Cliquez sur "Suivant"

5. **Étape 4 - Confirmation**
   - Vérifiez toutes vos informations
   - Cliquez sur "🚀 Rejoindre et commencer à jouer !"

6. **✅ C'est fait !**
   - Vous êtes automatiquement connecté
   - Vous êtes dans la maison de votre partenaire
   - Vous pouvez commencer à jouer !

## 🎯 Conseils

- **Code de maison** : Partagez-le uniquement avec les personnes de confiance
- **Plusieurs partenaires** : Vous pouvez inviter autant de personnes que vous voulez
- **SMS** : En développement, les SMS sont simulés (visibles dans la console)
- **Erreurs** : Si le code ne fonctionne pas, vérifiez qu'il est bien en majuscules

## 🔧 Test

Pour tester facilement toutes les fonctionnalités, accédez à :
```
http://127.0.0.1:5000/test_invitation
```

Cette page contient :
- Une explication détaillée de chaque étape
- Des liens directs vers les pages à tester
- Des cas de test recommandés
- Des données de test prêtes à l'emploi

## 📝 URLs importantes

- **Inviter des partenaires** : `/invite_partner`
- **Rejoindre une maison** : `/join_house`
- **Page de test** : `/test_invitation`
- **Se connecter** : `/login`
- **Menu principal** : `/menu`

## 🐛 Problèmes courants

### "Code de maison invalide"
- Vérifiez que le code est correct (6 caractères)
- Assurez-vous qu'il est en majuscules
- Demandez à votre partenaire de vérifier son code

### "Cet email est déjà utilisé"
- Cet email a déjà un compte
- Utilisez un autre email ou connectez-vous avec cet email

### "Le mot de passe doit contenir au moins 6 caractères"
- Créez un mot de passe plus long

### "Tous les champs sont requis"
- Remplissez tous les champs du formulaire

## 🎨 Fonctionnalités

✅ Invitation multiple (plusieurs partenaires à la fois)
✅ Interface intuitive et moderne
✅ Processus guidé en 4 étapes
✅ Validation en temps réel
✅ Messages d'erreur clairs
✅ Responsive (mobile et desktop)
✅ Connexion automatique après inscription
✅ Navigation avant/arrière dans le formulaire

## 📚 Documentation technique

Pour plus de détails techniques, consultez :
- `FLUX_INVITATION.md` : Architecture et flux complets
- `test_invitation.html` : Page de test interactive

Bon jeu ! 🎮✨
