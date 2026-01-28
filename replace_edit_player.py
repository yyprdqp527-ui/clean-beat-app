#!/usr/bin/env python3
import shutil
import os

source = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/edit_player_correct.html'
destination = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/edit_player.html'

try:
    # Copier le fichier
    shutil.copy2(source, destination)
    print(f"✓ Fichier copié avec succès")
    
    # Vérifier
    if os.path.exists(destination):
        with open(destination, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'dicebear' in content:
                print("✓ Code DiceBear trouvé dans le fichier")
            if 'generateDiceBearSeeds' in content:
                print("✓ Fonction generateDiceBearSeeds trouvée")
            print(f"✓ Fichier prêt ({len(content)} bytes)")
except Exception as e:
    print(f"✗ Erreur: {e}")
