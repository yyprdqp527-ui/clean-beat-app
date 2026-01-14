# 🏠 Comment résoudre le problème "Maison introuvable"

## 🔍 Qu'est-ce que ce message signifie ?

Le message "Maison introuvable" apparaît lorsque vous essayez d'accéder au jeu mais que votre compte n'est pas encore associé à une maison. CleanBeat fonctionne avec des **maisons partagées** où plusieurs personnes jouent ensemble !

## ✅ Solutions automatiques (mises en place)

### 1. Redirection automatique
Maintenant, au lieu d'afficher une erreur, l'application vous redirige automatiquement vers la page de création de maison !

### 2. Création automatique de maison
Quand vous accédez à la page d'invitation :
- **Une maison est créée automatiquement** avec un code unique
- Vous pouvez ensuite inviter des partenaires en partageant ce code
- Ou jouer seul·e si vous préférez

## 🎮 Comment rejoindre ou créer une maison ?

### Option A : Créer votre propre maison
1. Connectez-vous à votre compte
2. L'application vous redirigera vers `/invite_partner`
3. Une maison sera créée automatiquement avec un **code à 6 caractères**
4. Partagez ce code avec vos partenaires pour qu'ils vous rejoignent

### Option B : Rejoindre une maison existante
1. Demandez le **code de la maison** à la personne qui l'a créée
2. Allez sur `/join_house` ou cliquez sur "Rejoindre une maison"
3. Entrez le code de 6 caractères (ex: `ABC123`)
4. Créez votre compte en remplissant :
   - Votre nom
   - Votre email
   - Un mot de passe (minimum 6 caractères)

## 📱 Sur mobile

Le processus est identique sur mobile. Si vous voyez "Maison introuvable" :

1. **Vous serez redirigé automatiquement** vers la page de création de maison
2. Un message s'affichera : "Crée ou rejoins une maison pour commencer à jouer ! 🏠"
3. Suivez les étapes ci-dessus (Option A ou B)

## 🔧 Corrections apportées

Les modifications suivantes ont été implémentées :

1. ✅ Redirection automatique vers `/invite_partner` au lieu d'afficher une erreur
2. ✅ Création automatique d'une maison avec code unique
3. ✅ Messages explicatifs plus clairs
4. ✅ API améliorée avec instructions de redirection
5. ✅ Toutes les routes vérifient maintenant la présence d'une maison

## 💡 Conseils

- **Code de maison** : 6 caractères (lettres majuscules + chiffres)
- **Invitation** : Le code reste valide indéfiniment
- **Enfants** : Vous pouvez créer des profils enfants sans email
- **Solo** : Vous pouvez aussi jouer seul·e dans votre maison !

## 🆘 Besoin d'aide ?

Si le problème persiste :
1. Déconnectez-vous et reconnectez-vous
2. Vérifiez que vous avez bien un compte créé
3. Assurez-vous d'avoir accepté les cookies (nécessaires pour la session)
4. Essayez sur un autre navigateur si le problème persiste
