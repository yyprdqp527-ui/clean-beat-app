import io

# Check tasks.html CSS for .task-card background
lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/tasks.html', 'r', encoding='utf-8').readlines()
print("=== tasks.html .task-card CSS ===")
in_card = False
for i, l in enumerate(lines, 1):
    if '.task-card' in l:
        in_card = True
    if in_card:
        print(f"L{i}: {l.rstrip()[:200]}")
        if l.strip() == '' or (i > 1 and '}' in l and not '{' in l):
            in_card = False
        if i > 250:
            break
