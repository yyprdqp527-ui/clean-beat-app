#!/usr/bin/env python3
"""Supprime les 2èmes occurrences des pills mission/courses dans menu.html"""

f = open('templates/menu.html', 'r', encoding='utf-8')
lines = f.readlines()
f.close()

new_lines = []
skip_next = 0
i = 0
removed_blocks = 0

while i < len(lines):
    line = lines[i]
    
    # Détecter pill-mission (2ème occurrence à supprimer aussi)
    if 'pill-mission' in line and 'mission_messages' in line:
        # Supprimer les 4 lignes : div ouvrant, pill-icon, pill-count, div fermant
        i += 4  # skip 4 lines
        removed_blocks += 1
        continue
    
    # Détecter pill-courses (avec courses_messages ou reminders?from_badge)
    if 'pill-courses' in line and ('courses_messages' in line or 'courses_added' in line):
        i += 4
        removed_blocks += 1
        continue
    
    # Détecter lien /courses_messages dans profile-reminders (avec son contenu)
    if '/courses_messages' in line and 'profile-reminder-item' in line:
        # Supprimer jusqu'à la balise </a> fermante
        while i < len(lines) and '</a>' not in lines[i]:
            i += 1
        i += 1  # skip la ligne </a>
        removed_blocks += 1
        continue
    
    # Détecter lien /mission_messages dans profile-reminders
    if '/mission_messages' in line and 'profile-reminder-item' in line:
        while i < len(lines) and '</a>' not in lines[i]:
            i += 1
        i += 1
        removed_blocks += 1
        continue
    
    # Corriger total_rappels pour ne garder que unread_baby_tracking
    if 'total_rappels' in line and 'unread_courses' in line and 'unread_task_added' in line:
        line = line.replace(
            '(unread_courses|default(0)) + (unread_task_added|default(0)) + (unread_baby_tracking|default(0))',
            '(unread_baby_tracking|default(0))'
        )
    
    new_lines.append(line)
    i += 1

print(f"Blocs supprimés: {removed_blocks}")

f = open('templates/menu.html', 'w', encoding='utf-8')
f.writelines(new_lines)
f.close()
print("OK")
