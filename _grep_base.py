import io
path = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/base.html'
lines = io.open(path, 'r', encoding='utf-8').readlines()
for i, l in enumerate(lines, 1):
    if any(kw in l for kw in ['adaptive-text', 'adaptive', 'ULTRA', 'keep-color', 'bg_theme_light', 'bg_gradient']):
        print(f"L{i}: {l.rstrip()[:200]}")
