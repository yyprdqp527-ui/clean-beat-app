#!/usr/bin/env python3
"""Audit des pastilles (pills) dans menu.html"""
import subprocess

# Lire version actuelle
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    current = f.read()

# Lire version 9802acb
result = subprocess.run(['git', 'show', '9802acb:templates/menu.html'], 
                        capture_output=True, text=True)
ref = result.stdout

for label, content in [('9802acb', ref), ('ACTUEL', current)]:
    print(f'\n=== {label} ===')
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if any(kw in line for kw in ['pill-mission', 'pill-baby', 'pill-courses', 'updatePill']):
            stripped = line.strip()
            if not stripped.startswith('//') and not stripped.startswith('*') and not stripped.startswith('.'):
                print(f'  L{i+1}: {line.strip()[:200]}')
