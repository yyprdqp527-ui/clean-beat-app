import re
import os
import base64
import subprocess
import shutil

def fix_svg(svg_path):
    """Réparer le SVG avec les images compressées mais structure XML valide"""
    
    # Charger le fichier original (backup)
    original_path = svg_path + '.original'
    if not os.path.exists(original_path):
        print(f"Pas de backup trouvé pour {svg_path}")
        return
    
    with open(original_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Traitement de {svg_path}")
    print(f"  Taille originale: {len(content)/1024:.0f} Ko")
    
    # Extraire et compresser les images base64
    pattern = r'data:image/png;base64,([^"]+)'
    matches = list(re.finditer(pattern, content))
    
    temp_dir = os.path.dirname(svg_path)
    
    for i, match in enumerate(matches):
        b64_data = match.group(1)
        
        # Nettoyer le base64 des entités XML
        b64_clean = b64_data.replace('&#10;', '').replace('&#13;', '').replace('&#9;', '')
        b64_clean = b64_clean.replace('\n', '').replace('\r', '').replace(' ', '')
        
        # Ajouter padding si nécessaire
        padding = 4 - len(b64_clean) % 4
        if padding != 4:
            b64_clean += '=' * padding
        
        try:
            # Décoder le PNG
            png_data = base64.b64decode(b64_clean)
            png_path = os.path.join(temp_dir, f"_temp_{i}.png")
            jpeg_path = os.path.join(temp_dir, f"_temp_{i}.jpg")
            
            with open(png_path, 'wb') as f:
                f.write(png_data)
            
            # Redimensionner et convertir en JPEG avec sips
            subprocess.run(['sips', '--resampleWidth', '1024', png_path, '--out', png_path],
                          capture_output=True, text=True)
            subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '65',
                           png_path, '--out', jpeg_path],
                          capture_output=True, text=True)
            
            # Ré-encoder en base64
            with open(jpeg_path, 'rb') as f:
                jpeg_data = f.read()
            
            new_b64 = base64.b64encode(jpeg_data).decode('ascii')
            
            # Remplacer dans le SVG (garder la structure originale)
            old_full = f"data:image/png;base64,{b64_data}"
            new_full = f"data:image/jpeg;base64,{new_b64}"
            content = content.replace(old_full, new_full)
            
            print(f"  Image {i+1}: {len(b64_data)/1024:.0f} Ko -> {len(new_b64)/1024:.0f} Ko")
            
            # Nettoyer
            os.remove(png_path)
            os.remove(jpeg_path)
            
        except Exception as e:
            print(f"  Erreur image {i+1}: {e}")
    
    # Nettoyer les métadonnées Inkscape (sans casser le XML)
    # Supprimer les commentaires
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    # Supprimer l'élément sodipodi:namedview complet
    content = re.sub(r'<sodipodi:namedview[^>]*>.*?</sodipodi:namedview>', '', content, flags=re.DOTALL)
    
    # Supprimer les attributs inkscape/sodipodi des balises
    content = re.sub(r'\s+inkscape:[a-zA-Z\-]+="[^"]*"', '', content)
    content = re.sub(r'\s+sodipodi:[a-zA-Z\-]+="[^"]*"', '', content)
    
    print(f"  Taille finale: {len(content)/1024:.0f} Ko")
    print(f"  Réduction: {(1 - len(content)/len(re.sub(r'<!--.*?-->', '', open(original_path).read(), flags=re.DOTALL))/len(content)) * 100:.1f}%")
    
    # Sauvegarder
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(content)

# Traiter les 3 copies
base = "/Users/anne-gaelledaval/Downloads/Appli web-2/static/images"
paths = [
    os.path.join(base, "maisonwoop.svg"),
    os.path.join(base, "bonus", "maisonwoop.svg"),
    os.path.join(base, "buanderie", "maisonwoop.svg"),
]

for p in paths:
    if os.path.exists(p + '.original'):
        fix_svg(p)
        print()

print("Terminé!")
