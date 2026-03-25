import io

path = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html'
with io.open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

targets = ['room-new-mission-badge', 'room-mission-dot', 'room-baby-dot']

for i, line in enumerate(lines, 1):
    for t in targets:
        if t in line:
            # Show context: what kind of line is it?
            tag = ''
            if '<span' in line: tag = 'HTML_SPAN'
            elif 'querySelector' in line: tag = 'JS_query'
            elif 'forEach' in line: tag = 'JS_forEach'
            elif '{' in line and '.' in line and 'css' not in line.lower(): tag = 'CSS_or_JS'
            else: tag = '???'
            print(f"L{i:5d} [{tag}] {line[:150].rstrip()}")
