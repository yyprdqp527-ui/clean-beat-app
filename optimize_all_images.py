#!/usr/bin/env python3
"""
Script pour optimiser toutes les images WebP de CleanBeat
Réduit la taille des images tout en maintenant une qualité acceptable
"""

import os
import subprocess
from pathlib import Path

def get_file_size_kb(filepath):
    """Retourne la taille du fichier en KB"""
    return os.path.getsize(filepath) / 1024

def optimize_image(image_path, max_size_kb=150, quality=75):
    """
    Optimise une image WebP
    - max_size_kb: taille maximale cible en KB
    - quality: qualité de compression (1-100)
    """
    original_size = get_file_size_kb(image_path)
    
    if original_size <= max_size_kb:
        return False, original_size, original_size
    
    # Créer une copie de sauvegarde temporaire
    backup_path = f"{image_path}.backup"
    subprocess.run(['cp', image_path, backup_path], check=True)
    
    try:
        # Optimiser l'image avec ImageMagick
        cmd = [
            'magick', 
            image_path,
            '-resize', '800x800>',  # Redimensionner si > 800px
            '-quality', str(quality),
            '-define', 'webp:method=6',  # Meilleure compression
            image_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Restaurer la sauvegarde en cas d'erreur
            subprocess.run(['mv', backup_path, image_path], check=True)
            return False, original_size, original_size
        
        new_size = get_file_size_kb(image_path)
        
        # Si toujours trop grand, réduire encore la qualité
        if new_size > max_size_kb and quality > 60:
            cmd[cmd.index('-quality') + 1] = '60'
            subprocess.run(cmd, check=True)
            new_size = get_file_size_kb(image_path)
        
        # Supprimer la sauvegarde
        os.remove(backup_path)
        
        return True, original_size, new_size
        
    except Exception as e:
        # Restaurer en cas d'erreur
        if os.path.exists(backup_path):
            subprocess.run(['mv', backup_path, image_path], check=True)
        print(f"❌ Erreur pour {image_path}: {e}")
        return False, original_size, original_size

def main():
    """Optimise toutes les images WebP du projet"""
    
    print("🚀 Optimisation des images CleanBeat\n")
    
    # Vérifier si ImageMagick est installé
    try:
        subprocess.run(['magick', '--version'], capture_output=True, check=True)
    except:
        print("❌ ImageMagick n'est pas installé!")
        print("   Installez-le avec: brew install imagemagick")
        return
    
    images_dir = Path('static/images')
    
    if not images_dir.exists():
        print("❌ Dossier static/images introuvable!")
        return
    
    # Trouver toutes les images WebP
    webp_files = list(images_dir.rglob('*.webp'))
    
    print(f"📊 {len(webp_files)} images trouvées\n")
    
    optimized_count = 0
    total_saved = 0
    errors = []
    
    for i, image_path in enumerate(webp_files, 1):
        relative_path = image_path.relative_to(images_dir)
        
        success, original, new = optimize_image(str(image_path))
        
        if success:
            saved = original - new
            total_saved += saved
            optimized_count += 1
            reduction = ((original - new) / original * 100) if original > 0 else 0
            
            print(f"[{i}/{len(webp_files)}] ✅ {relative_path}")
            print(f"       {original:.0f}KB → {new:.0f}KB (-{reduction:.0f}%)")
        else:
            if original > 150:
                print(f"[{i}/{len(webp_files)}] ⚠️  {relative_path} ({original:.0f}KB - trop volumineuse)")
                errors.append((str(relative_path), original))
            else:
                print(f"[{i}/{len(webp_files)}] ✓  {relative_path} ({original:.0f}KB - OK)")
    
    # Résumé
    print("\n" + "="*60)
    print(f"✅ Images optimisées: {optimized_count}/{len(webp_files)}")
    print(f"💾 Espace économisé: {total_saved:.0f}KB ({total_saved/1024:.1f}MB)")
    
    if errors:
        print(f"\n⚠️  {len(errors)} images nécessitent une attention manuelle:")
        for path, size in errors[:10]:
            print(f"   - {path} ({size:.0f}KB)")
        if len(errors) > 10:
            print(f"   ... et {len(errors)-10} autres")
    
    print("\n✨ Optimisation terminée!")

if __name__ == '__main__':
    main()
