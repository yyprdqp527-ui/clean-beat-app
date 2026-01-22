#!/usr/bin/env python3
"""
Script interactif pour vous aider à remplacer les images CleanBeat
Fournit des suggestions de recherche et automatise l'optimisation
"""

import os
import subprocess
from pathlib import Path

# Suggestions de recherche pour chaque image
SEARCH_SUGGESTIONS = {
    "cuisine": {
        "ranger la vaiselle dans le placard.webp": ["dishes in cupboard", "organizing kitchen cabinet"],
        "faire_course.webp": ["grocery shopping cart", "supermarket shopping"],
        "faire à manger.webp": ["cooking kitchen", "preparing meal"],
        "mettre la table.webp": ["setting table", "dinner table setting"],
        "lave vaiselle.webp": ["dishwasher loading", "clean dishes"],
        "passer l'eponge.webp": ["wiping counter", "cleaning kitchen surface"],
        "nettoyer le plan de travil.webp": ["cleaning countertop", "wiping kitchen counter"],
        "netoyer le frigo.webp": ["cleaning refrigerator", "organized fridge"],
    },
    "salon": {
        "Ranger le desordre du salon.webp": ["tidy living room", "organizing living space"],
        "faire la poussière.webp": ["dusting furniture", "cleaning dust"],
        "arroser les plantes.webp": ["watering plants", "plant care"],
        "Passer l'aspirateur.webp": ["vacuuming carpet", "vacuum cleaner"],
        "laver les vitres.webp": ["cleaning windows", "window washing"],
        "laver les sols.webp": ["mopping floor", "cleaning floor"],
    },
    "chambre ados": {
        "Ranger sa chambre.webp": ["tidy bedroom teen", "organizing room"],
        "Faire ses devoirs.webp": ["student studying homework", "teenager homework"],
        "mettre ses vetements dans le panier à linge.webp": ["laundry basket clothes", "dirty clothes hamper"],
        "aérer sa chambre.webp": ["opening window fresh air", "ventilating room"],
        "vider sa corbeille à papier.webp": ["emptying trash bin", "waste basket"],
        "faire son lit.webp": ["making bed", "tidy bed sheets"],
    },
    "chambre bébé": {
        "donner le biberon.webp": ["baby bottle feeding", "infant feeding"],
        "changer les couches.webp": ["changing diaper", "baby diaper change"],
        "laver les vêtements.webp": ["baby clothes washing", "infant laundry"],
        "laver les biberons.webp": ["washing baby bottles", "cleaning bottles"],
        "endormir le bébé.webp": ["baby sleeping peacefully", "putting baby to sleep"],
    },
    "salle de bain": {
        "nettoyer les poils de barbe.webp": ["cleaning sink beard", "bathroom sink clean"],
        "nettoyer les cheveux.webp": ["cleaning hair drain", "bathroom hair"],
        "se laver es dents.webp": ["brushing teeth", "toothbrush"],
        "reboucher le dentifrice.webp": ["toothpaste cap", "closing toothpaste"],
        "éponger le sol.webp": ["mopping bathroom floor", "bathroom cleaning"],
    },
    "buanderie": {
        "linge etendu.webp": ["hanging laundry", "clothes drying line"],
        "linge plié.webp": ["folded clothes", "folding laundry"],
        "ranger ses vetements.webp": ["organizing clothes closet", "wardrobe organization"],
    },
    "chambre parent": {
        "faire le lit.webp": ["making bed adult", "tidy bedroom"],
        "changer les draps du lit.webp": ["changing bed sheets", "fresh bedding"],
        "ranger ses vetements.webp": ["organizing wardrobe", "closet organization"],
    },
    "chambre enfant": {
        "ranger ses jouets.webp": ["organizing toys", "toy storage"],
        "lire dix minutes par jour.webp": ["child reading book", "kid reading"],
    },
    "wc": {
        "laver_toillettes.webp": ["cleaning toilet", "bathroom toilet clean"],
        "séjourner aux toilettes.webp": ["bathroom restroom", "toilet icon"],
    },
    "garage": {
        "carwash.webp": ["car wash", "washing car"],
        "contrôle technique .webp": ["car inspection", "vehicle maintenance"],
        "Prendre de l'essence.webp": ["gas station refueling", "petrol pump"],
    },
    "bonus": {
        "penser au gouter.webp": ["kids snack", "afternoon snack"],
        "organiser les anniversaire.webp": ["birthday party planning", "celebration"],
        "signer les mots.webp": ["signing school papers", "parent signature"],
        "prendre les rdv médicaux.webp": ["doctor appointment", "medical calendar"],
        "déclarer les impôts.webp": ["tax forms", "filing taxes"],
        "aller aux reunions d'ecole.webp": ["parent teacher meeting", "school meeting"],
    },
}

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def main():
    print_header("🎨 Assistant de remplacement d'images CleanBeat")
    
    print("Ce script vous aide à remplacer vos images par des alternatives")
    print("plus authentiques (photos réelles ou banques d'images).\n")
    
    print("📍 Sites recommandés pour télécharger des images :")
    print("   • Unsplash.com - Photos professionnelles")
    print("   • Pexels.com - Grande variété")
    print("   • Pixabay.com - Millions d'images libres")
    print("   • unDraw.co - Illustrations modernes\n")
    
    images_dir = Path('static/images')
    
    if not images_dir.exists():
        print("❌ Dossier static/images introuvable!")
        return
    
    while True:
        print("\nQue souhaitez-vous faire ?")
        print("  1. Voir les suggestions de recherche par catégorie")
        print("  2. Lister toutes les images à remplacer")
        print("  3. Optimiser de nouvelles images ajoutées")
        print("  4. Quitter")
        
        choice = input("\nVotre choix (1-4) : ").strip()
        
        if choice == "1":
            print_header("Suggestions de recherche par catégorie")
            for category, images in SEARCH_SUGGESTIONS.items():
                print(f"\n📁 {category.upper()}")
                print("-" * 60)
                for img_name, searches in images.items():
                    print(f"\n  📷 {img_name}")
                    print(f"     Recherches suggérées :")
                    for search in searches:
                        print(f"       • {search}")
                
                input("\n[Appuyez sur Entrée pour continuer...]")
        
        elif choice == "2":
            print_header("Liste complète des images à remplacer")
            
            total = 0
            for category in SEARCH_SUGGESTIONS.keys():
                category_path = images_dir / category
                if category_path.exists():
                    images = list(category_path.glob('*.webp'))
                    total += len(images)
                    print(f"\n📁 {category} ({len(images)} images)")
                    for img in sorted(images):
                        size_kb = img.stat().st_size / 1024
                        print(f"   • {img.name} ({size_kb:.0f}KB)")
            
            print(f"\n📊 TOTAL : {total} images à remplacer")
        
        elif choice == "3":
            print_header("Optimisation des nouvelles images")
            print("Lancement de l'optimisation automatique...\n")
            subprocess.run(['python3', 'optimize_all_images.py'])
        
        elif choice == "4":
            print("\n✨ Bon courage pour le remplacement de vos images !")
            print("📖 Consultez GUIDE_REMPLACEMENT_IMAGES.md pour plus d'infos\n")
            break
        
        else:
            print("❌ Choix invalide, réessayez.")

if __name__ == '__main__':
    main()
