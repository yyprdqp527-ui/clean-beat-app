# 🎨 Guide de remplacement des images CleanBeat

## Problème
Les images actuelles ont un aspect trop "généré par IA" et manquent d'authenticité.

## Solutions sans savoir dessiner

### ✅ Option 1 : Photos réelles (RECOMMANDÉ)
**Avantages** : Authentique, gratuit, rapide
**Comment faire** :
1. Prenez des photos avec votre téléphone de chaque tâche
2. Utilisez l'appareil photo de votre iPhone/Android
3. Prenez des photos claires, bien éclairées
4. Exemple : Pour "Faire la vaisselle", prenez une photo de votre évier avec de la vaisselle

**Script fourni** : `replace_images.py` vous aidera à renommer et optimiser vos photos

### ✅ Option 2 : Photos gratuites en ligne
**Sites recommandés** :
- **Unsplash.com** - Photos professionnelles gratuites
- **Pexels.com** - Grande variété, usage commercial autorisé
- **Pixabay.com** - Millions d'images libres de droits

**Recherches suggérées** (en anglais pour plus de résultats) :
- "washing dishes" → Faire la vaisselle
- "making bed" → Faire le lit
- "vacuum cleaner" → Passer l'aspirateur
- "folding clothes" → Plier le linge
- "cleaning bathroom" → Nettoyer la salle de bain
- etc.

### ✅ Option 3 : Illustrations simples
**Sites d'illustrations gratuites** :
- **unDraw.co** - Illustrations modernes personnalisables (couleurs)
- **Storyset.com** - Illustrations par thème (maison, nettoyage)
- **Flaticon.com** - Icônes vectorielles (version gratuite avec attribution)

## 📋 Liste des images à remplacer (62 images)

### Cuisine (12 images)
- [ ] ranger la vaiselle dans le placard.webp
- [ ] cuisine.webp
- [ ] faire_course.webp
- [ ] livraisonUber.webp
- [ ] cusine.webp
- [ ] faire à manger.webp
- [ ] mettre la table.webp
- [ ] ranger la vaiselle.webp
- [ ] lave vaiselle.webp
- [ ] passer l'eponge.webp
- [ ] nettoyer le plan de travil.webp
- [ ] netoyer le frigo.webp

### Salon (6 images)
- [ ] Ranger le desordre du salon.webp
- [ ] faire la poussière.webp
- [ ] arroser les plantes.webp
- [ ] Passer l'aspirateur.webp
- [ ] laver les vitres.webp
- [ ] laver les sols.webp

### Chambre Ado (7 images)
- [ ] chambre ado.webp
- [ ] Ranger sa chambre.webp
- [ ] Faire ses devoirs.webp
- [ ] mettre ses vetements dans le panier à linge.webp
- [ ] aérer sa chambre.webp
- [ ] vider sa corbeille à papier.webp
- [ ] faire son lit.webp

### Chambre Bébé (6 images)
- [ ] donner le biberon.webp
- [ ] vider la poubelle.webp
- [ ] changer les couches.webp
- [ ] laver les vêtements.webp
- [ ] laver les biberons.webp
- [ ] endormir le bébé.webp

### Salle de bain (6 images)
- [ ] jeter les bouteilles de savon vide. wepb.webp
- [ ] nettoyer les poils de barbe.webp
- [ ] nettoyer les cheveux.webp
- [ ] se laver es dents.webp
- [ ] reboucher le dentifrice.webp
- [ ] éponger le sol.webp

### Buanderie (3 images)
- [ ] linge etendu.webp
- [ ] linge plié.webp
- [ ] ranger ses vetements.webp

### Chambre Parent (3 images)
- [ ] faire le lit.webp
- [ ] changer les draps du lit.webp
- [ ] ranger ses vetements.webp

### Chambre Enfant (2 images)
- [ ] ranger ses jouets.webp
- [ ] lire dix minutes par jour.webp

### WC (2 images)
- [ ] laver_toillettes.webp
- [ ] séjourner aux toilettes.webp

### Garage (3 images)
- [ ] carwash.webp
- [ ] contrôle technique .webp
- [ ] Prendre de l'essence.webp

### Bonus (6 images)
- [ ] penser au gouter.webp
- [ ] organiser les anniversaire.webp
- [ ] signer les mots.webp
- [ ] prendre les rdv médicaux.webp
- [ ] déclarer les impôts.webp
- [ ] aller aux reunions d'ecole.webp

### Récompenses (6 images)
- [ ] dispensé de corvée pour une journée.webp
- [ ] deux heures d'ecran supplementaire.webp
- [ ] petit dej au lit recompense.webp
- [ ] trier les poubelles.webp
- [ ] debarras.webp
- [ ] Ménage à Deux.webp

## 🚀 Processus de remplacement

### Méthode manuelle
1. Téléchargez vos nouvelles images
2. Renommez-les EXACTEMENT comme les anciennes (respectez la casse et les accents)
3. Placez-les dans le bon dossier (`static/images/[catégorie]/`)
4. Optimisez-les avec : `python3 optimize_all_images.py`

### Méthode assistée (script fourni)
```bash
python3 replace_images.py
```
Ce script vous guidera étape par étape pour :
- Lister les images à remplacer
- Vous suggérer des recherches pour chaque image
- Optimiser automatiquement les nouvelles images

## 📏 Spécifications techniques
- **Format** : WebP (ou JPG/PNG, le script convertit automatiquement)
- **Taille recommandée** : 800x800 pixels max
- **Poids cible** : < 150 KB par image
- **Qualité** : 75% (bon compromis qualité/poids)

## 💡 Conseils pratiques

### Pour des photos réussies :
1. ✅ Bonne lumière naturelle
2. ✅ Cadrage simple et centré
3. ✅ Arrière-plan propre
4. ✅ Focus sur l'action/objet principal
5. ❌ Éviter les photos floues ou sombres

### Gain de temps :
- Faites toutes les photos d'une même pièce en une session
- Utilisez le même angle/lumière pour cohérence visuelle
- Prenez 2-3 variantes de chaque photo au cas où

## 🎯 Prochaines étapes
1. Choisissez votre méthode (photos perso ou banques d'images)
2. Commencez par une catégorie (ex: Cuisine)
3. Testez avec 3-4 images
4. Si satisfait, continuez avec le reste
5. Utilisez `optimize_all_images.py` à la fin

---

**Besoin d'aide ?** Les scripts Python fournis automatisent la plupart du travail !
