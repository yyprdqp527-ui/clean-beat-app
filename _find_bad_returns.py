#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Chercher tous les scripts
in_script = False
script_num = 0
script_start = 0

for i, line in enumerate(lines, 1):
    if '<script>' in line:
        in_script = True
        script_start = i
        script_num += 1
        brace_count = 0
    
    if in_script:
        brace_count += line.count('{')
        brace_count -= line.count('}')
        
        # Détecter les return quand brace_count est suspect
        if 'return' in line and not line.strip().startswith('//') and not line.strip().startswith('*'):
            if brace_count <= 0:
                print(f"🔴 SCRIPT #{script_num} - Ligne {i}: return avec balance={brace_count}")
                print(f"   {line.strip()[:100]}")
                
                # Montrer le contexte
                start_ctx = max(script_start, i-5)
                print(f"   Contexte (lignes {start_ctx}-{i}):")
                for j in range(start_ctx-1, i):
                    print(f"     {j+1}: {lines[j].rstrip()[:80]}")
                print()
    
    if '</script>' in line and in_script:
        final_balance = brace_count
        if final_balance != 0:
            print(f"⚠️  SCRIPT #{script_num} ({script_start}-{i}): balance finale = {final_balance}")
        in_script = False
