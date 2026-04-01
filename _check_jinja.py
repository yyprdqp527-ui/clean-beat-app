#!/usr/bin/env python3
"""Analyse le nesting Jinja2 dans menu.html pour trouver les erreurs."""
import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
errors = []

for i, line in enumerate(lines):
    # Chercher tous les tags Jinja2 de contrôle
    for m in re.finditer(r'\{%-?\s*(if|elif|else|endif|for|endfor|block|endblock)\b', line):
        tag = m.group(1)
        if tag in ('if', 'for', 'block'):
            stack.append((tag, i+1))
        elif tag in ('elif', 'else'):
            # Ces tags ne changent pas la profondeur
            if not stack or stack[-1][0] != 'if':
                errors.append(f'L{i+1}: {{% {tag} %}} sans {{% if %}} correspondant (top: {stack[-1] if stack else "VIDE"})')
        elif tag in ('endif', 'endfor', 'endblock'):
            expected = tag[3:]  # 'if' from 'endif', 'for' from 'endfor'
            if stack and stack[-1][0] == expected:
                stack.pop()
            else:
                top = stack[-1] if stack else ('VIDE', 0)
                errors.append(f'L{i+1}: {{% {tag} %}} mais attendu {{% end{top[0]} %}} (ouvert L{top[1]})')
                # Ne pas break, continuer pour voir les autres erreurs
                # Essayer de récupérer en cherchant dans la stack
                found = False
                for j in range(len(stack)-1, -1, -1):
                    if stack[j][0] == expected:
                        # Il y avait un tag non fermé entre les deux
                        unclosed = stack[j+1:]
                        for u in unclosed:
                            errors.append(f'  -> {{% {u[0]} %}} non fermé (L{u[1]})')
                        stack = stack[:j]
                        found = True
                        break
                if not found:
                    errors.append(f'  -> Pas de {{% {expected} %}} correspondant dans la stack')

if errors:
    print(f'ERREURS TROUVEES: {len(errors)}')
    for e in errors:
        print(f'  {e}')
    print()

if stack:
    print(f'Tags non fermés à la fin: {len(stack)}')
    for tag, ln in stack:
        print(f'  {{% {tag} %}} à la ligne {ln}')
else:
    if not errors:
        print('Aucune erreur de nesting Jinja2 trouvée')
