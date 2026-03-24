#!/usr/bin/env python3
# coding: utf-8
"""Audit des !important dans les CSS ajoutés"""

with open('templates/gameplay.html', encoding='utf-8') as f:
    c = f.read()
with open('templates/classement.html', encoding='utf-8') as f:
    c2 = f.read()

print(f"gameplay.html : {len(c)} chars")
print(f"classement.html : {len(c2)} chars")
print()

checks = [
    (c,  '.feature-title {'),
    (c,  '.feature-subtitle {'),
    (c,  '.wheel-validate-btn {'),
    (c,  '.wheel-validate-btn.done {'),
    (c,  '.wheel-pts-counter {'),
    (c,  '.wheel-pts-counter strong {'),
    (c,  '.wtc-name {'),
    (c,  '.wtc-pts {'),
    (c,  '.spin-btn {'),
    (c,  '.malus-sheet-title {'),
    (c,  '.malus-option-label {'),
    (c,  '.malus-option-pts {'),
    (c,  '.wheel-result-title {'),
    (c,  '.wheel-result-btn {'),
    (c2, '.cw-task-time {'),
    (c2, '.cw-pts {'),
]

for src, cls in checks:
    idx = src.find(cls)
    if idx == -1:
        print(f"  {cls}: NON TROUVE")
        continue
    # Prendre le snippet jusqu'au prochain }
    end = src.find('}', idx)
    snippet = src[idx:end+1]
    has_imp = '!important' in snippet
    color_line = [l.strip() for l in snippet.split('\n') if 'color' in l]
    color_str = color_line[0][:60] if color_line else snippet[:60]
    status = "OK" if has_imp else "MANQUE"
    print(f"  [{status}] {cls} -> {color_str}")
