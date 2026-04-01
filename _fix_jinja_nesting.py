#!/usr/bin/env python3
"""Répare les blocs Jinja2 cassés par la suppression des avatar-notification-badge."""

FILE = 'templates/menu.html'

with open(FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'Lignes avant: {len(lines)}')

def find_line(text, start=0):
    for i in range(start, len(lines)):
        if text in lines[i]:
            return i
    return -1

fixes = 0

# Fix 1: Bloc p2 — après "{% elif p2.is_child_account %}" + commentaire enfant
idx = find_line('elif p2.is_child_account')
if idx >= 0:
    # La ligne suivante devrait être le commentaire {# C'est un ENFANT #}
    next_idx = idx + 1
    if 'ENFANT' in lines[next_idx]:
        # Il manque les lignes set/else/set/endif APRÈS le commentaire
        # Vérifier que la ligne après le commentaire est directement le <div class="vbar
        after_comment = next_idx + 1
        if '<div class="vbar simple"' in lines[after_comment]:
            # Insérer les lignes manquantes
            indent1 = '                                                '  # 48 espaces
            indent2 = '                                            '      # 44 espaces
            insert_lines = [
                indent1 + '{% set p2_unread = children_unread.get(p2.email, 0) if children_unread else 0 %}\n',
                indent2 + '{% else %}\n',
                indent1 + '{# C\'est un AUTRE ADULTE → pas de pastille #}\n',
                indent1 + '{% set p2_unread = 0 %}\n',
                indent2 + '{% endif %}\n',
            ]
            for j, line in enumerate(insert_lines):
                lines.insert(after_comment + j, line)
            fixes += 1
            print(f'Fix 1: Bloc p2 réparé (5 lignes insérées après L{after_comment+1})')
        else:
            print(f'Info: Bloc p2 déjà OK (ligne après commentaire: {lines[after_comment].strip()[:60]})')
    else:
        print(f'WARN: Pas de commentaire ENFANT après elif p2.is_child_account')
else:
    print('WARN: elif p2.is_child_account non trouvé')

# Fix 2: Bloc p — après "{% elif p.is_child_account %}" + commentaire enfant
idx = find_line('elif p.is_child_account')
if idx >= 0:
    next_idx = idx + 1
    if 'ENFANT' in lines[next_idx]:
        after_comment = next_idx + 1
        if '<div class="vbar simple"' in lines[after_comment]:
            indent1 = '                                                    '  # 52 espaces
            indent2 = '                                                '      # 48 espaces
            insert_lines = [
                indent1 + '{% set p_unread = children_unread.get(p.email, 0) if children_unread else 0 %}\n',
                indent2 + '{% else %}\n',
                indent1 + '{# C\'est un AUTRE ADULTE → pas de pastille #}\n',
                indent1 + '{% set p_unread = 0 %}\n',
                indent2 + '{% endif %}\n',
            ]
            for j, line in enumerate(insert_lines):
                lines.insert(after_comment + j, line)
            fixes += 1
            print(f'Fix 2: Bloc p réparé (5 lignes insérées après L{after_comment+1})')
        else:
            print(f'Info: Bloc p déjà OK (ligne après commentaire: {lines[after_comment].strip()[:60]})')
    else:
        print(f'WARN: Pas de commentaire ENFANT après elif p.is_child_account')
else:
    print('WARN: elif p.is_child_account non trouvé')

with open(FILE, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'\nLignes après: {len(lines)} ({fixes} fix(es) appliqué(es))')
