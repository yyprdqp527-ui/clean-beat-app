"""
Fix images de missions :
1. Mettre à NULL les task_image qui pointent vers des fichiers manquants
2. Convertir les images existantes sur disque en data URI (base64 en DB)
3. Compresser les images trop grosses
"""
import sqlite3, os, base64

try:
    from PIL import Image, ImageOps
    import io
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    print("⚠️ Pillow non installé — pas de compression")

conn = sqlite3.connect('users.db')
c = conn.cursor()

c.execute("SELECT id, task_name, task_image, category FROM custom_tasks WHERE task_image IS NOT NULL AND task_image != ''")
rows = c.fetchall()

fixed = 0
converted = 0
nulled = 0

for tid, name, img, cat in rows:
    # Déjà un data URI → OK
    if img.startswith('data:'):
        continue
    
    # Vérifier si le fichier existe
    path = os.path.join('static', 'images', img)
    if not os.path.exists(path):
        # Fichier manquant → mettre à NULL
        c.execute("UPDATE custom_tasks SET task_image = NULL WHERE id = ?", (tid,))
        nulled += 1
        print(f"  🗑  ID {tid:4d} | {name[:35]:35s} | fichier manquant → NULL")
        continue
    
    # Fichier existe → convertir en data URI compressé
    if HAS_PILLOW:
        try:
            img_pil = Image.open(path)
            img_pil = ImageOps.exif_transpose(img_pil)
            img_pil = img_pil.convert('RGB')
            img_pil.thumbnail((800, 800), Image.LANCZOS)
            buf = io.BytesIO()
            img_pil.save(buf, format='JPEG', quality=80, optimize=True)
            image_data = buf.getvalue()
            
            data_uri = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
            c.execute("UPDATE custom_tasks SET task_image = ? WHERE id = ?", (data_uri, tid))
            
            orig_size = os.path.getsize(path) / 1024
            new_size = len(data_uri) / 1024
            converted += 1
            print(f"  ✅  ID {tid:4d} | {name[:35]:35s} | {orig_size:.0f} Ko → {new_size:.0f} Ko data-URI")
        except Exception as e:
            print(f"  ❌  ID {tid:4d} | {name[:35]:35s} | Erreur: {e}")
    else:
        # Sans Pillow, juste lire et encoder en base64 (pas de compression)
        with open(path, 'rb') as f:
            raw = f.read()
        data_uri = f"data:image/jpeg;base64,{base64.b64encode(raw).decode('utf-8')}"
        c.execute("UPDATE custom_tasks SET task_image = ? WHERE id = ?", (data_uri, tid))
        converted += 1
        print(f"  ✅  ID {tid:4d} | {name[:35]:35s} | converti sans compression")

conn.commit()
conn.close()

print(f"\n=== TERMINÉ ===")
print(f"Images manquantes nettoyées (→ NULL): {nulled}")
print(f"Images converties en data URI: {converted}")
print(f"Total corrigé: {nulled + converted}")
