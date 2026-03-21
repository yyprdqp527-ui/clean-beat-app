import re

content = open('templates/menu.html', encoding='utf-8').read()
orig_len = len(content)

# 1. Pill HTML dans le burger header
# Chercher le pattern plus souple
pattern1 = r'<div class="burger-alert-pill baby"[^>]*>.*?</div>'
m = re.search(pattern1, content, re.DOTALL)
if m:
    content = content[:m.start()] + content[m.end():]
    print('✅ 1. pill HTML burger supprimée')
else:
    print('❌ 1. pill HTML burger non trouvée')

# 2. CSS .header-action-pill.pill-baby block
pattern2 = r'\.header-action-pill\.pill-baby \{[^}]+\}\n?'
m2 = re.search(pattern2, content)
if m2:
    content = content[:m2.start()] + content[m2.end():]
    print('✅ 2. CSS pill-baby supprimé')
else:
    print('❌ 2. CSS non trouvé')

# 3. CSS .burger-alert-pill.baby block (si existe séparément)
pattern3 = r'\.burger-alert-pill\.baby \{[^}]+\}\n?'
m3 = re.search(pattern3, content)
if m3:
    content = content[:m3.start()] + content[m3.end():]
    print('✅ 3. CSS burger-alert-pill.baby supprimé')
else:
    print('ℹ️  3. CSS burger-alert-pill.baby non trouvé (OK)')

# 4. JS updatePill pill-baby
old4 = "updatePill('pill-baby', 'pill-baby-count', counts.unread_baby || 0);"
idx4 = content.find(old4)
if idx4 != -1:
    # Supprimer la ligne entière
    start = content.rfind('\n', 0, idx4) + 1
    end = content.find('\n', idx4) + 1
    content = content[:start] + content[end:]
    print('✅ 4. JS updatePill pill-baby supprimé')
else:
    print('❌ 4. JS updatePill non trouvé')

# 5. unread_baby dans totalBadge
old5 = ' + (counts.unread_baby || 0)'
if old5 in content:
    content = content.replace(old5, '', 1)
    print('✅ 5. unread_baby totalBadge supprimé')
else:
    print('❌ 5. unread_baby totalBadge non trouvé')

# 6. Bloc rappel baby dans le profil burger ({% if has_baby_tracking %}...{% endif %})
pattern6 = r'\{%- ?if has_baby_tracking ?-?%\}.*?\{%- ?endif ?-?%\}'
m6 = re.search(pattern6, content, re.DOTALL)
if m6:
    content = content[:m6.start()] + content[m6.end():]
    print('✅ 6. rappel baby profil supprimé')
else:
    # Essai sans tirets
    pattern6b = r'\{% if has_baby_tracking %\}.*?\{% endif %\}'
    m6b = re.search(pattern6b, content, re.DOTALL)
    if m6b:
        content = content[:m6b.start()] + content[m6b.end():]
        print('✅ 6. rappel baby profil supprimé (variante)')
    else:
        print('❌ 6. rappel baby profil non trouvé')

print(f'\nTaille: {orig_len} → {len(content)} ({orig_len - len(content)} chars supprimés)')
open('templates/menu.html', 'w', encoding='utf-8').write(content)
print('✅ Fichier sauvegardé')
