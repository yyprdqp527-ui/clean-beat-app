#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extraire chaque script et le sauvegarder
in_script = False
script_num = 0
script_lines = []
script_start = 0

for i, line in enumerate(lines, 1):
    if '<script>' in line:
        in_script = True
        script_start = i
        script_num += 1
        script_lines = []
    elif '</script>' in line and in_script:
        # Sauvegarder ce script
        if script_lines:
            filename = f'/tmp/script_{script_num}.js'
            with open(filename, 'w', encoding='utf-8') as f_out:
                f_out.write('\n'.join(script_lines))
            print(f"📜 Script #{script_num} ({script_start}-{i}): {len(script_lines)} lignes → {filename}")
        in_script = False
    elif in_script:
        script_lines.append(line.rstrip())

print(f"\n✅ {script_num} scripts extraits dans /tmp/")
print("🔍 Testez-les avec: node --check /tmp/script_X.js")
