import io, os

base = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates'

# Templates qui etendent base.html ou ont du CSS color-related
templates = [
    'task_page_enhanced.html',
    'tasks.html',
    'add_task.html',
    'add_custom_task.html',
]

for fname in templates:
    p = os.path.join(base, fname)
    if not os.path.exists(p):
        print(f"NOT FOUND: {fname}")
        continue
    lines = io.open(p, 'r', encoding='utf-8').readlines()
    print(f"\n=== {fname} ({len(lines)} lines) ===")
    # Lignes with 'card', 'color:', 'background', '#fff', 'white'
    for i, l in enumerate(lines, 1):
        lstr = l.lower()
        if ('background' in lstr or '#fff' in lstr or 'white' in lstr) and 'color' not in lstr:
            # Just background, find card-related
            if 'card' in lstr:
                print(f"  L{i}: {l.rstrip()[:180]}")
        if 'color' in lstr and ('card' in lstr or 'task' in lstr or '.input' in lstr or 'input' in lstr):
            print(f"  L{i}: {l.rstrip()[:180]}")
    print()

# Check base.html extends logic 
lines_base = io.open(os.path.join(base, 'base.html'), 'r', encoding='utf-8').readlines()
print(f"=== base.html extends/block content ===")
for i, l in enumerate(lines_base, 1):
    if 'extends\|block\|endblock' in l.lower() or '{%' in l:
        if 'block' in l or 'extends' in l:
            print(f"  L{i}: {l.rstrip()[:180]}")
    if i > 30:
        break
