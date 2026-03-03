import re
import os
import xml.etree.ElementTree as ET

paths = [
    "/Users/anne-gaelledaval/Downloads/Appli web-2/static/images/maisonwoop.svg",
    "/Users/anne-gaelledaval/Downloads/Appli web-2/static/images/bonus/maisonwoop.svg",
    "/Users/anne-gaelledaval/Downloads/Appli web-2/static/images/buanderie/maisonwoop.svg",
]

for svg_path in paths:
    with open(svg_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_size = len(content)
    
    # Supprimer les éléments inkscape complets (balises auto-fermantes et ouvrantes/fermantes)
    content = re.sub(r'<inkscape:[^>]*/>', '', content)
    content = re.sub(r'<inkscape:[^>]*>.*?</inkscape:[^>]*>', '', content, flags=re.DOTALL)
    
    # Supprimer les éléments sodipodi complets
    content = re.sub(r'<sodipodi:[^>]*/>', '', content)
    content = re.sub(r'<sodipodi:[^>]*>.*?</sodipodi:[^>]*>', '', content, flags=re.DOTALL)
    
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ {os.path.basename(os.path.dirname(svg_path))}/{os.path.basename(svg_path)}")
    print(f"  Taille: {len(content)/1024:.0f} Ko (était {original_size/1024:.0f} Ko)")

print("\n--- Vérification XML ---")
try:
    tree = ET.parse(paths[0])
    root = tree.getroot()
    print(f"✓ SVG valide XML!")
    print(f"  Dimensions: {root.get('width')}x{root.get('height')}")
except Exception as e:
    print(f"✗ Erreur XML: {e}")
