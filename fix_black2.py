from PIL import Image
import os

folder = '/Users/anne-gaelledaval/Downloads/Appli web-2/static/images'
to_fix = [
    'chambre bébé4 .webp',
    'Wc2.webp',
    'buanderie5.webp',
    'Garage2.webp',
]

for img_name in to_fix:
    path = os.path.join(folder, img_name)
    if not os.path.exists(path):
        print(f'ABSENT: {img_name}')
        continue
    try:
        img = Image.open(path).convert('RGBA')
        pixels = img.load()
        w, h = img.size
        count = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if r < 30 and g < 30 and b < 30:
                    pixels[x, y] = (r, g, b, 0)
                    count += 1
        img.save(path, 'WEBP', quality=80, method=6)
        size_ko = os.path.getsize(path) // 1024
        print(f'OK {img_name}: {count} px noirs supprimés → {size_ko}Ko')
    except Exception as e:
        print(f'ERREUR {img_name}: {e}')

print('DONE')
