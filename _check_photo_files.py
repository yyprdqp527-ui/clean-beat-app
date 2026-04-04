import sqlite3, os

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Toutes les images de missions
c.execute("SELECT id, task_name, task_image, category FROM custom_tasks WHERE task_image IS NOT NULL AND task_image != ''")
rows = c.fetchall()

print(f"=== {len(rows)} missions avec image ===\n")

data_uri_count = 0
file_count = 0
file_exists_count = 0
file_missing_count = 0
missing_list = []

for r in rows:
    tid, name, img, cat = r
    if img.startswith('data:'):
        data_uri_count += 1
        size_kb = len(img) / 1024
        print(f"  OK  ID {tid:4d} | {cat:20s} | {name[:30]:30s} | data-URI {size_kb:.0f} Ko")
    else:
        file_count += 1
        # Check if file exists in static/images/
        path = os.path.join('static', 'images', img)
        exists = os.path.exists(path)
        if exists:
            fsize = os.path.getsize(path) / 1024
            file_exists_count += 1
            print(f"  OK  ID {tid:4d} | {cat:20s} | {name[:30]:30s} | fichier {fsize:.0f} Ko | {img[:40]}")
        else:
            file_missing_count += 1
            missing_list.append((tid, name, img, cat))
            print(f"  ❌  ID {tid:4d} | {cat:20s} | {name[:30]:30s} | MANQUANT | {img[:40]}")

print(f"\n=== RÉSUMÉ ===")
print(f"Data URIs (en DB, OK): {data_uri_count}")
print(f"Fichiers sur disque: {file_count}")
print(f"  - Existants: {file_exists_count}")
print(f"  - MANQUANTS: {file_missing_count}")

if missing_list:
    print(f"\n=== FICHIERS MANQUANTS ===")
    for tid, name, img, cat in missing_list:
        print(f"  ID {tid} | {cat} | {name} | {img}")

conn.close()
