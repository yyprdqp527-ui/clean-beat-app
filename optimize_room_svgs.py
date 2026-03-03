#!/usr/bin/env python3
"""
Optimise les SVGs de pièces isométriques exportés depuis Illustrator.
Transforme les milliers de classes CSS en attributs inline fill/fill-rule,
supprime le bloc <defs><style>, réduit massivement la taille.
"""
import re, sys
from pathlib import Path

def optimize_svg(input_path: str, output_path: str):
    src = Path(input_path).read_text(encoding='utf-8')

    # 1. Extraire toutes les règles CSS du bloc <style>
    style_match = re.search(r'<style[^>]*>(.*?)</style>', src, re.DOTALL)
    if not style_match:
        print(f"⚠️  Pas de bloc <style> trouvé dans {input_path}")
        Path(output_path).write_text(src, encoding='utf-8')
        return

    style_text = style_match.group(1)

    # 2. Parser les règles CSS : .stNNN { prop: value; prop: value; }
    class_styles: dict[str, dict[str, str]] = {}
    for rule in re.finditer(r'((?:\.[a-zA-Z_][a-zA-Z0-9_-]*\s*,?\s*)+)\s*\{([^}]*)\}', style_text):
        selectors_raw = rule.group(1)
        declarations = rule.group(2)
        # Parser les propriétés
        props: dict[str, str] = {}
        for decl in re.finditer(r'([\w-]+)\s*:\s*([^;]+)', declarations):
            props[decl.group(1).strip()] = decl.group(2).strip()
        # Associer à chaque sélecteur
        for sel in re.finditer(r'\.([a-zA-Z_][a-zA-Z0-9_-]*)', selectors_raw):
            cls = sel.group(1)
            if cls not in class_styles:
                class_styles[cls] = {}
            class_styles[cls].update(props)

    print(f"  → {len(class_styles)} classes CSS trouvées")

    # 3. Remplacer les attributs class="stXXX stYYY ..." par des attributs inline
    def replace_class_attr(m):
        tag_start = m.group(1)   # balise + attributs avant class
        classes_str = m.group(2) # valeur de class
        tag_end = m.group(3)     # reste de la balise

        # Fusionner les styles de toutes les classes
        merged: dict[str, str] = {}
        for cls in classes_str.split():
            if cls in class_styles:
                merged.update(class_styles[cls])

        if not merged:
            # Pas de style connu, garder class tel quel
            return m.group(0)

        # Construire les attributs inline
        attrs = ''
        for prop, val in merged.items():
            # Convertir fill-rule -> fill-rule attr, fill -> fill attr, etc.
            attrs += f' {prop}="{val}"'

        return f'{tag_start}{attrs}{tag_end}'

    # Pattern pour matcher class="..." dans les balises SVG
    # On cible les éléments graphiques (path, polygon, polyline, rect, circle, ellipse, line)
    result = re.sub(
        r'(<(?:path|polygon|polyline|rect|circle|ellipse|line|g)\b[^>]*?)\s+class="([^"]+)"([^>]*>)',
        replace_class_attr,
        src
    )

    # 4. Supprimer le bloc <defs> s'il ne contient que <style>
    # D'abord supprimer le style block
    result = re.sub(r'\s*<style[^>]*>.*?</style>\s*', '\n', result, flags=re.DOTALL)
    # Supprimer <defs></defs> vides ou contenant uniquement des espaces
    result = re.sub(r'<defs[^>]*>\s*</defs>', '', result)

    # 5. Supprimer le commentaire Generator Illustrator
    result = re.sub(r'\s*<!-- Generator:.*?-->', '', result)

    # 6. Supprimer version="1.1" et xmlns:xlink si xlink non utilisé
    if 'xlink:href' not in result and 'xlink:' not in result:
        result = result.replace(' xmlns:xlink="http://www.w3.org/1999/xlink"', '')
    result = result.replace(' version="1.1"', '')

    # 7. Nettoyer les espaces multiples dans les attributs
    result = re.sub(r'  +', ' ', result)

    Path(output_path).write_text(result, encoding='utf-8')

    orig_size = Path(input_path).stat().st_size
    new_size = Path(output_path).stat().st_size
    reduction = (1 - new_size / orig_size) * 100
    print(f"  ✅ {Path(input_path).name}: {orig_size:,} → {new_size:,} octets ({reduction:.0f}% de réduction)")


if __name__ == '__main__':
    base = Path(__file__).parent / 'static' / 'images'
    files = [
        ('cuisinewoop.svg', 'cuisinewoop_v2.svg'),
        ('sdbwoop.svg', 'sdbwoop_v2.svg'),
    ]
    for src_name, dst_name in files:
        src_path = base / src_name
        dst_path = base / dst_name
        if src_path.exists():
            print(f"\n📦 Optimisation de {src_name}...")
            optimize_svg(str(src_path), str(dst_path))
        else:
            print(f"❌ Fichier non trouvé : {src_path}")

    print("\n✨ Terminé !")
