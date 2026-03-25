import io
# Check tasks.html for .task-card background color definitions
lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/tasks.html', 'r', encoding='utf-8').readlines()
print("=== tasks.html - background and color in CSS ===")
for i, l in enumerate(lines, 1):
    lstr = l.lower()
    if 'background' in lstr and '.task-card' in lstr:
        print(f"L{i}: {l.rstrip()[:180]}")
    if 'task-card' in lstr and ('background' in lstr or 'color' in lstr):
        print(f"L{i}: {l.rstrip()[:180]}")

# Check all input/textarea/select in templates that extend base.html
import os
base = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates'
for fname in os.listdir(base):
    if not fname.endswith('.html'): continue
    content = io.open(os.path.join(base, fname), 'r', encoding='utf-8').read()
    if 'base.html' not in content and '{% extends' not in content:
        # Only check templates that use base styles
        continue
    # Find input/textarea with explicit background colors
    if 'input' in content.lower() and ('background' in content.lower() or 'color' in content.lower()):
        pass  # too broad, skip
print("\n=== Checking which templates extend base.html ===")
for fname in os.listdir(base):
    if not fname.endswith('.html'): continue
    content = io.open(os.path.join(base, fname), 'r', encoding='utf-8').read()
    if "{% extends 'base.html'" in content or '{% extends "base.html"' in content:
        print(f"  extends base: {fname}")
