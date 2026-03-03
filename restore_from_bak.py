from PIL import Image
import os

folder = '/Users/anne-gaelledaval/Downloads/Appli web-2/static/images'
TARGET_W, TARGET_H = 600, 693

# Images à restaurer depuis leur .bak (RGBA original propre)
to_restore = [
    'chambre1.webp',
    'chambre2.webp',
    'chambreparentale marron.webp',
    'cuisinewoop.webp',
    'salonorange.webp',
    'sdbwoop.webp',
    'chambre bébé4 .webp',
]

for img_name in to_restore:
    bak_path = os.path.join(folder, img_name + '.bak')
    out_path = os.path.join(folder, img_name)

    if not os.path.exists(bak_path):
        print(f'PAS DE .BAK: {img_name} — ignoré')
        continue

    try:
        img = Image.open(bak_path)
        # Garder RGBA pour conserver la transparence propre avec anti-aliasing
        img_rgba = img.convert('RGBA')
        # Redimensionner en gardant le mode RGBA (Lanczos = anti-aliasing propre)
        img_resized = img_rgba.resize((TARGET_W, TARGET_H), Image.LANCZOS)
        # Sauvegarder en WebP avec transparence
        img_resized.save(out_path, 'WEBP', quality=82, method=6)
        size_ko = os.path.getsize(out_path) // 1024
        print(f'✅ {img_name}: RGBA {TARGET_W}x{TARGET_H} → {size_ko}Ko')
    except Exception as e:
        print(f'❌ ERREUR {img_name}: {e}')

print('DONE')
