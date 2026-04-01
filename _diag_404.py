import re, glob

with open('app.py', 'r') as f:
    app_content = f.read()

# Extraire les routes Flask
routes = set()
for m in re.finditer(r"@app\.route\('([^']+)'", app_content):
    routes.add(m.group(1))

# Extraire les fetch calls depuis les templates
missing = []
for tpl in glob.glob('templates/*.html'):
    with open(tpl, 'r') as f:
        content = f.read()
    for m in re.finditer(r"""fetch\(\s*['"`](/api/[^'"`?]+)""", content):
        url = m.group(1)
        if url not in routes:
            found = False
            for r in routes:
                if '<' in r:
                    pattern = re.sub(r'<[^>]+>', '[^/]+', r)
                    if re.match(pattern + '$', url):
                        found = True
                        break
            if not found:
                line_no = content[:m.start()].count('\n') + 1
                fname = tpl.split('/')[-1]
                missing.append(f'{fname}:L{line_no} -> {url}')

if missing:
    print('=== ROUTES MANQUANTES (fetch dans templates sans route Flask) ===')
    for m in missing:
        print(f'  {m}')
else:
    print('Toutes les API appelees en fetch existent dans les routes Flask.')

# Aussi check les window.location / href vers des pages
print()
print('=== Routes de page (non-API) ===')
page_routes = [r for r in routes if not r.startswith('/api/') and not r.startswith('/static')]
for r in sorted(page_routes):
    print(f'  {r}')
