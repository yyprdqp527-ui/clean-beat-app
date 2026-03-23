#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Chercher le script qui contient openBurgerMenu  
in_script = False
script_start = 0
script_num = 0

for i, line in enumerate(lines, 1):
    if '<script>' in line:
        in_script = True
        script_start = i
        script_num += 1
    
    # Trouver le script qui contient openBurgerMenu
    if in_script and 'window.openBurgerMenu' in line:
        print(f"📜 openBurgerMenu trouvé dans SCRIPT #{script_num}, ligne {i}")
        print(f"   Script a commencé ligne {script_start}")
        
        # Compter les accolades de ce script jusqu'à openBurgerMenu
        brace_count = 0
        for j in range(script_start-1, i):
            brace_count += lines[j].count('{')
            brace_count -= lines[j].count('}')
        
        print(f"   Balance d'accolades jusqu'à openBurgerMenu: {brace_count}")
        
        # Chercher le </script>
        for j in range(i, min(len(lines), i+2000)):
            if '</script>' in lines[j]:
                print(f"   Script finit ligne {j+1}")
                
                # Balance totale du script
                total_brace = 0
                for k in range(script_start-1, j):
                    total_brace += lines[k].count('{')
                    total_brace -= lines[k].count('}')
                
                print(f"   Balance totale: {total_brace}")
                if total_brace != 0:
                    print(f"   🔴 DÉSÉQUILIBRE: {total_brace} accolades manquantes!")
                else:
                    print("   ✅ Accolades équilibrées")
                break
        break
    
    if '</script>' in line:
        in_script = False
