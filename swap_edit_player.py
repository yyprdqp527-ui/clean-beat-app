import shutil
import os

templates_dir = "/Users/anne-gaelledaval/Downloads/Appli web-2/templates"

# Sauvegarder l'ancien fichier
old_file = os.path.join(templates_dir, "edit_player.html")
backup_file = os.path.join(templates_dir, "edit_player_backup.html")
new_file = os.path.join(templates_dir, "edit_player_simple.html")

# Faire la sauvegarde
if os.path.exists(old_file):
    shutil.move(old_file, backup_file)
    print(f"✓ Ancien fichier sauvegardé: {backup_file}")

# Renommer le nouveau fichier
if os.path.exists(new_file):
    shutil.move(new_file, old_file)
    print(f"✓ Nouveau fichier activé: {old_file}")
    
print("\n✅ Fichiers remplacés avec succès!")
