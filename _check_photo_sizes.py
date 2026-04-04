import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# 1. Photos de missions (custom_tasks)
c.execute("SELECT id, task_name, category, LENGTH(task_image) as img_len FROM custom_tasks WHERE task_image IS NOT NULL ORDER BY img_len DESC LIMIT 15")
rows = c.fetchall()
print("=== Photos de missions (custom_tasks) ===")
print(f"Total avec photo: {len(rows)}")
for r in rows:
    size_kb = r[3] / 1024 if r[3] else 0
    starts = ""
    # Check if it's a data URI
    c.execute("SELECT SUBSTR(task_image, 1, 30) FROM custom_tasks WHERE id=?", (r[0],))
    prefix = c.fetchone()[0]
    starts = "data-URI" if prefix and prefix.startswith("data:") else f"fichier: {prefix}"
    print(f"  ID {r[0]:4d} | {r[2]:20s} | {r[1][:35]:35s} | {size_kb:8.1f} Ko | {starts}")

# 2. Photos de preuve (proof_requests)
try:
    c.execute("SELECT id, task_name, LENGTH(photo_data) as photo_len, status FROM proof_requests WHERE photo_data IS NOT NULL ORDER BY photo_len DESC LIMIT 10")
    rows2 = c.fetchall()
    print(f"\n=== Photos de preuve (proof_requests) ===")
    print(f"Total avec photo: {len(rows2)}")
    for r in rows2:
        size_kb = r[2] / 1024 if r[2] else 0
        print(f"  ID {r[0]:4d} | {r[1][:35]:35s} | {size_kb:8.1f} Ko | status: {r[3]}")
except Exception as e:
    print(f"proof_requests: {e}")

# 3. Avatars photo (data URI)
c.execute("SELECT email, name, LENGTH(avatar_url) as len FROM users WHERE avatar_url LIKE 'data:%' ORDER BY len DESC LIMIT 10")
rows3 = c.fetchall()
print(f"\n=== Avatars photo (users.avatar_url data URI) ===")
print(f"Total: {len(rows3)}")
for r in rows3:
    size_kb = r[2] / 1024 if r[2] else 0
    print(f"  {r[1]:20s} | {size_kb:8.1f} Ko")

# 4. Vérifier les custom_tasks SANS compression (très gros)
c.execute("SELECT COUNT(*) FROM custom_tasks WHERE task_image IS NOT NULL AND LENGTH(task_image) > 500000")
big = c.fetchone()[0]
print(f"\n=== ALERTES ===")
print(f"Images missions > 500Ko: {big}")

c.execute("SELECT COUNT(*) FROM custom_tasks WHERE task_image IS NOT NULL AND LENGTH(task_image) > 100000")
medium = c.fetchone()[0]
print(f"Images missions > 100Ko: {medium}")

c.execute("SELECT COUNT(*) FROM custom_tasks WHERE task_image IS NOT NULL")
total = c.fetchone()[0]
print(f"Total images missions: {total}")

if total > 0:
    c.execute("SELECT AVG(LENGTH(task_image)) FROM custom_tasks WHERE task_image IS NOT NULL")
    avg = c.fetchone()[0]
    print(f"Taille moyenne: {avg/1024:.1f} Ko")

conn.close()
