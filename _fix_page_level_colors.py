import io, os

base_dir = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates'

# Remplacer les sélecteurs de page-level qui ont des couleurs hardcodées foncées
# sur des éléments DIRECTS sur le fond de page (h1 container-menu, etc.)
fixes = [
    # tasks.html: titre de catégorie directement potentiellement sur le fond
    {
        'file': 'tasks.html',
        'old': '.container-menu h1 { color:#000; }',
        'new': '.container-menu h1 { color: var(--adaptive-text, #153036); }'
    },
]

for fix in fixes:
    p = os.path.join(base_dir, fix['file'])
    if not os.path.exists(p):
        print(f"NOT FOUND: {fix['file']}")
        continue
    content = io.open(p, 'r', encoding='utf-8').read()
    if fix['old'] in content:
        content = content.replace(fix['old'], fix['new'], 1)
        io.open(p, 'w', encoding='utf-8').write(content)
        print(f"FIXED {fix['file']}: {fix['old'][:60]}")
    else:
        print(f"NOT FOUND in {fix['file']}: {fix['old'][:60]}")

# Vérifier tasks.html: 
# La section "Activités récentes" L758 a color:#153036 inline dans HTML
# -> c'est dans un contexte de container glass, pas directement sur le bg
# Ne pas modifier ces cas (ils sont dans des conteneurs à fond blanc/glass)

print("\nDone. Fixing tasks.html page-level colors.")

# BONUS: also look for add_task.html L23 (body? or container?)
content_add = io.open(os.path.join(base_dir, 'add_task.html'), 'r', encoding='utf-8').readlines()
for i in range(15, 35):
    print(f"add_task.html L{i+1}: {content_add[i].rstrip()[:180]}")
