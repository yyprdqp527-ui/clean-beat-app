from PIL import Image
import os

folder = '/Users/anne-gaelledaval/Downloads/Appli web-2/static/images'
to_fix = [
    'chambre1.webp',
    'chambre2.webp',
    'chambreparentale marron.webp',
    'cuisinewoop.webp',
    'salonorange.webp',
    'sdbwoop.webp',
    'deux heures d\'ecran supplementaire.webp',
    'dispensé de corvée pour une journée.webp',
]

for img_name in to_fix:
    path = os.path.join(folder, img_name)
    if not os.path.exists(path):
        print(f'MANQUANT: {img_name}')
        continue
    try:
        img = Image.open(path)
        w, h = img.size
        print(f'{img_name}: {img.mode} {w}x{h}')
    except Exception as e:
        print(f'ERREUR {img_name}: {e}')

print('DONE')
