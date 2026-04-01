import re

path = 'templates/menu.html'
lines = open(path, encoding='utf-8').readlines()

# Afficher les lignes avec _total
for i, l in enumerate(lines):
    if '_total' in l:
        print(i+1, repr(l.rstrip()))
