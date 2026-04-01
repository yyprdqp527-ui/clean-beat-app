path = 'templates/menu.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

old = (
    "                window.addEventListener('pageshow', function(event) {\n"
    "                    console.log('🔄 pageshow event, persisted=' + event.persisted);\n"
    "                    // Restaurer IMMEDIATEMENT depuis sessionStorage (zero delai)"
)

new = (
    "                window.addEventListener('pageshow', function(event) {\n"
    "                    console.log('🔄 pageshow event, persisted=' + event.persisted);\n"
    "                    // Restauration bfcache : recharger pour avoir les badges Jinja2 frais\n"
    "                    if (event.persisted) {\n"
    "                        console.log('🔄 bfcache -> rechargement complet');\n"
    "                        window.location.reload();\n"
    "                        return;\n"
    "                    }\n"
    "                    // Restaurer IMMEDIATEMENT depuis sessionStorage (zero delai)"
)

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK modification appliquee')
else:
    # Afficher ce qui est autour de "pageshow" pour debug
    idx = content.find("addEventListener('pageshow'")
    if idx >= 0:
        print('TROUVE pageshow à idx', idx)
        print(repr(content[idx-30:idx+200]))
    else:
        print('pageshow non trouve du tout')
