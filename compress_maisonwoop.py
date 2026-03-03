import re
import os
import base64
import subprocess
import shutil

base = "/Users/anne-gaelledaval/Downloads/Appli web-2/static/images"
svg_files = [
    os.path.join(base, "maisonwoop.svg"),
    os.path.join(base, "bonus", "maisonwoop.svg"),
    os.path.join(base, "buanderie", "maisonwoop.svg"),
]

# Travailler sur la copie principale d'abord
svg_path = svg_files[0]

with open(svg_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Taille originale: {len(content)/1024:.0f} Ko")

# Extraire les images base64
pattern = r'(data:image/png;base64,)([^"]+)'
matches = list(re.finditer(pattern, content))
print(f"Images trouvees: {len(matches)}")

new_content = content
for i, match in enumerate(matches):
    b64_data = match.group(2)
    
    # Nettoyer et corriger le padding base64
    b64_clean = b64_data.replace('\n', '').replace('\r', '').replace(' ', '')
    b64_clean = b64_clean.replace('&#10;', '').replace('&#13;', '').replace('&#9;', '')
    # Ajouter le padding manquant
    padding = 4 - len(b64_clean) % 4
    if padding != 4:
        b64_clean += '=' * padding
    
    # Décoder le PNG
    png_data = base64.b64decode(b64_clean)
    png_path = os.path.join(base, f"_temp_img_{i}.png")
    webp_path = os.path.join(base, f"_temp_img_{i}.webp")
    
    with open(png_path, 'wb') as f:
        f.write(png_data)
    
    png_size = os.path.getsize(png_path)
    print(f"  Image {i+1} PNG: {png_size/1024:.0f} Ko")
    
    # Convertir en WebP compressé avec sips (natif macOS)
    # D'abord réduire la résolution si très grande
    result = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', png_path], 
                          capture_output=True, text=True)
    print(f"  Dimensions: {result.stdout.strip()}")
    
    # Redimensionner si trop grand (max 1024px de large)
    subprocess.run(['sips', '--resampleWidth', '1024', png_path, '--out', png_path],
                  capture_output=True, text=True)
    
    # Convertir en JPEG compressé (sips supporte ça nativement)
    jpeg_path = os.path.join(base, f"_temp_img_{i}.jpg")
    subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '60',
                   png_path, '--out', jpeg_path],
                  capture_output=True, text=True)
    
    jpeg_size = os.path.getsize(jpeg_path)
    print(f"  Image {i+1} JPEG: {jpeg_size/1024:.0f} Ko")
    
    # Ré-encoder en base64
    with open(jpeg_path, 'rb') as f:
        jpeg_data = f.read()
    
    new_b64 = base64.b64encode(jpeg_data).decode('ascii')
    
    # Remplacer dans le SVG
    old_str = f"data:image/png;base64,{b64_data}"
    new_str = f"data:image/jpeg;base64,{new_b64}"
    new_content = new_content.replace(old_str, new_str)
    
    print(f"  Base64: {len(b64_data)/1024:.0f} Ko -> {len(new_b64)/1024:.0f} Ko")
    
    # Nettoyer les fichiers temp
    os.remove(png_path)
    os.remove(jpeg_path)

# Aussi nettoyer les métadonnées Inkscape
new_content = re.sub(r'<!--.*?-->', '', new_content, flags=re.DOTALL)
new_content = re.sub(r'<sodipodi:namedview[^>]*?>.*?</sodipodi:namedview>', '', new_content, flags=re.DOTALL)
new_content = re.sub(r'\s+inkscape:\w+="[^"]*"', '', new_content)
new_content = re.sub(r'\s+sodipodi:\w+="[^"]*"', '', new_content)
new_content = re.sub(r'\s+xmlns:inkscape="[^"]*"', '', new_content)
new_content = re.sub(r'\s+xmlns:sodipodi="[^"]*"', '', new_content)
new_content = re.sub(r'\n\s*\n+', '\n', new_content)

print(f"\nTaille finale: {len(new_content)/1024:.0f} Ko")
print(f"Reduction: {(1 - len(new_content)/len(content)) * 100:.1f}%")

# Sauvegarder
for svg_file in svg_files:
    if os.path.exists(svg_file):
        backup = svg_file + '.original'
        if not os.path.exists(backup):
            shutil.copy2(svg_file, backup)
        with open(svg_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        new_size = os.path.getsize(svg_file)
        print(f"Sauvegarde: {svg_file} ({new_size/1024:.0f} Ko)")

print("\nTermine!")
