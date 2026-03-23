#!/usr/bin/env python3
import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Chercher des patterns problématiques
in_script = False
script_start = 0
brace_depth = 0
paren_depth = 0
func_stack = []

for i, line in enumerate(lines, 1):
    if '<script>' in line or '<script ' in line:
        in_script = True
        script_start = i
        brace_depth = 0
        paren_depth = 0
        func_stack = []
    elif '</script>' in line:
        if brace_depth != 0:
            print(f"⚠️  Script à ligne {script_start}: accolades déséquilibrées (depth={brace_depth})")
        in_script = False
    
    if in_script:
        # Compter accolades et parenthèses
        for char in line:
            if char == '{':
                brace_depth += 1
            elif char == '}':
                brace_depth -= 1
                if func_stack and brace_depth < func_stack[-1]:
                    func_stack.pop()
            elif char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
        
        # Détecter les fonctions
        if re.search(r'\bfunction\s+\w+|\bfunction\s*\(|=>\s*\{', line):
            func_stack.append(brace_depth - 1)
        
        # Chercher return hors fonction
        if 'return' in line and ';' in line:
            if not func_stack:
                print(f"⚠️  Ligne {i}: 'return' hors de toute fonction")
                print(f"     {line.strip()[:80]}")
                print(f"     Stack: {func_stack}, depth: {brace_depth}")
                print()

print("Vérification terminée")
