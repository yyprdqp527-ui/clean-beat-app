import io

# Vérifier Fix 1: room-baby-dot dans menu.html
menu = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html', 'r', encoding='utf-8').read()
lines = menu.splitlines()
for i, l in enumerate(lines, 1):
    if 'room-baby-dot' in l:
        print(f"menu.html L{i}: {l[:200]}")

print()

# Vérifier Fix 2: get_unread_count_by_type dans app.py
app = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/app.py', 'r', encoding='utf-8').read()
alines = app.splitlines()
for i, l in enumerate(alines, 1):
    if 'get_unread_count_by_type' in l and 'baby_tracking' in l:
        print(f"app.py L{i}: {l[:200]}")
print()
for i, l in enumerate(alines, 1):
    if 'def get_unread_count_by_type' in l:
        print(f"app.py L{i}: {l[:200]}")
    if 'include_own' in l:
        print(f"app.py L{i}: {l[:180]}")
