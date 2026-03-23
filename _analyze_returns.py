#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Analyser chaque bloc <script>
in_script = False
script_num = 0
brace_balance = 0
problem_lines = []

for i, line in enumerate(lines, 1):
    if '<script>' in line:
        in_script = True
        script_num += 1
        brace_balance = 0
        print(f"\n📜 SCRIPT #{script_num} commence ligne {i}")
    
    if in_script:
        # Compter les accolades
        opens = line.count('{')
        closes = line.count('}')
        brace_balance += opens - closes
        
        # Détecter les return potentiellement problématiques
        if 'return' in line and not line.strip().startswith('//') and not line.strip().startswith('*'):
            # Vérifier si on est vraiment dans une fonction
            # Un return valide a généralement un brace_balance > 0
            if brace_balance <= 1:  # Seuil: si proche de 0, probablement hors fonction
                problem_lines.append((i, line.strip(), brace_balance))
                print(f"  ⚠️  Ligne {i} (balance={brace_balance}): {line.strip()[:80]}")
    
    if '</script>' in line and in_script:
        print(f"📜 Script #{script_num} finit ligne {i}")
        print(f"   Balance finale: {brace_balance}")
        if brace_balance != 0:
            print(f"   🔴 DÉSÉQUILIBRE: {brace_balance} accolades!")
        in_script = False

print(f"\n\n📊 RÉSUMÉ: {len(problem_lines)} return potentiellement problématiques trouvés")
if problem_lines:
    print("\n🔍 Lignes à vérifier:")
    for line_num, content, balance in problem_lines:
        print(f"  • Ligne {line_num} (balance {balance}): {content[:100]}")
