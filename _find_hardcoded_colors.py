import io, os

base = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates'

# Check for hardcoded dark colors (#153036, teal, dark) on page-level elements
# in templates that extend base.html
dark_colors = ['#153036', '#597176', 'teal-dark', 'teal-light']

templates_to_check = [
    'tasks.html',
    'task_page_enhanced.html',
    'reminders.html',
    'completed_tasks.html',
    'add_task.html',
    'add_custom_task.html',
    'comments.html',
    'baby_tracking.html',
    'profil.html',
]

for fname in templates_to_check:
    p = os.path.join(base, fname)
    if not os.path.exists(p): continue
    lines = io.open(p, 'r', encoding='utf-8').readlines()
    hits = []
    for i, l in enumerate(lines, 1):
        lstr = l.lower()
        # Page-level text elements with hardcoded dark colors (not in .task-card or similar)
        if 'color' in lstr:
            if any(dc in l for dc in dark_colors) or '#153036' in l or '153036' in l:
                # Skip if it's clearly inside a card CSS with its own background
                card_context = any(c in l for c in ['.task-card', '.card-', '.badge', '.btn-', '.avatar'])
                if not card_context:
                    hits.append(f"  L{i}: {l.rstrip()[:180]}")

    if hits:
        print(f"\n=== {fname}: hardcoded dark colors on page elements ===")
        for h in hits[:20]:
            print(h)
