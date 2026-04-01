#!/usr/bin/env python3
"""Diagnostic markTypeRead dans menu.html"""
path = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html'
f = open(path, 'r', encoding='utf-8')
lines = f.readlines()
f.close()

count = sum(1 for l in lines if 'markTypeRead' in l)
print(f'Occurrences markTypeRead: {count}')
print()

for i, line in enumerate(lines):
    if 'markTypeRead' in line:
        print(f'L{i+1}: {line.rstrip()[:200]}')

print()
for i, line in enumerate(lines):
    if 'function markTypeRead' in line:
        print(f'=== function markTypeRead à L{i+1} ===')
        for j in range(i, min(i+15, len(lines))):
            print(f'  {j+1}: {lines[j].rstrip()[:160]}')
        print()
