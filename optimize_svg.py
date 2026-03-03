import re
import os
import shutil

def optimize_svg(svg_path):
    with open(svg_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_size = len(content)

    # Supprimer les commentaires
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # Supprimer les éléments sodipodi:namedview entiers
    content = re.sub(r'<sodipodi:namedview[^>]*>.*?</sodipodi:namedview>', '', content, flags=re.DOTALL)
    content = re.sub(r'<sodipodi:namedview[^/]*/>', '', content, flags=re.DOTALL)

    # Supprimer les attributs Inkscape/Sodipodi
    content = re.sub(r'\s+inkscape:\w+="[^"]*"', '', content)
    content = re.sub(r'\s+sodipodi:\w+="[^"]*"', '', content)
    content = re.sub(r'\s+xml:space="[^"]*"', '', content)

    # Supprimer les déclarations de namespace inkscape/sodipodi
    content = re.sub(r'\s+xmlns:inkscape="[^"]*"', '', content)
    content = re.sub(r'\s+xmlns:sodipodi="[^"]*"', '', content)

    # Supprimer les id inutiles (générés automatiquement)
    content = re.sub(r'\s+id="(defs|stop|clipPath|rect|path|linearGradient|radialGradient|g)\d+[^"]*"', '', content)

    # Supprimer les lignes vides multiples
    content = re.sub(r'\n\s*\n+', '\n', content)
    
    # Supprimer les espaces entre les balises
    content = re.sub(r'>\s+<', '><', content)

    new_size = len(content)

    # Sauvegarder le SVG original en backup
    backup_path = svg_path + '.backup'
    if not os.path.exists(backup_path):
        shutil.copy2(svg_path, backup_path)

    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  Original: {original_size / 1024:.0f} Ko")
    print(f"  Optimise: {new_size / 1024:.0f} Ko")
    print(f"  Reduction: {(1 - new_size/original_size) * 100:.1f}%")
    return new_size

base = "/Users/anne-gaelledaval/Downloads/Appli web-2/static/images"
paths = [
    os.path.join(base, "maisonwoop.svg"),
    os.path.join(base, "bonus", "maisonwoop.svg"),
    os.path.join(base, "buanderie", "maisonwoop.svg"),
]

total_saved = 0
for p in paths:
    if os.path.exists(p):
        print(f"\n{p}:")
        optimize_svg(p)
    else:
        print(f"\n{p}: INTROUVABLE")

# Afficher les tailles finales
print("\n--- Tailles finales ---")
for p in paths:
    if os.path.exists(p):
        size = os.path.getsize(p)
        print(f"  {p}: {size/1024:.0f} Ko")
