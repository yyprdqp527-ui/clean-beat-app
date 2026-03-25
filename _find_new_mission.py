import io
path = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html'
lines = io.open(path, 'r', encoding='utf-8').readlines()
for i, l in enumerate(lines, 1):
    if 'room-new-mission-badge' in l:
        print(i, l[:200].rstrip())
