#!/usr/bin/env python3
"""Applique TOUTES les modifications : retries, bfcache, nettoyage code mort.
   Travaille ligne par ligne pour éviter les problèmes de regex DOTALL."""

FILE = 'templates/menu.html'

with open(FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'Fichier chargé : {len(lines)} lignes')

def find_line(text, start=0):
    """Trouve le premier index de ligne contenant le texte exact."""
    for i in range(start, len(lines)):
        if text in lines[i]:
            return i
    return -1

def find_line_exact(text, start=0):
    """Trouve la ligne dont le .strip() == text."""
    for i in range(start, len(lines)):
        if lines[i].strip() == text:
            return i
    return -1

changes = []

# ═══════════════════════════════════════════════════════════
# A. RETRIES dans refreshAllBadges
# ═══════════════════════════════════════════════════════════
idx = find_line('function refreshAllBadges()')
if idx >= 0:
    # Remplacer la signature
    lines[idx] = lines[idx].replace('function refreshAllBadges()', 'function refreshAllBadges(_attempt)')
    # Insérer les lignes de retry après la signature
    indent = '                    '
    lines.insert(idx+1, indent + '_attempt = _attempt || 0;\n')
    lines.insert(idx+2, indent + 'var _retryDelays = [500, 1500, 4000];\n')
    changes.append('A1. refreshAllBadges signature + retryDelays')
    
    # Remplacer le .then(r) simple par un bloc avec retry
    idx2 = find_line(".then(function(r) { if (!r.ok) return null; return r.json(); })", idx)
    if idx2 >= 0:
        indent2 = '                        '
        lines[idx2:idx2+1] = [
            indent2 + '.then(function(r) {\n',
            indent2 + '    if (!r.ok) {\n',
            indent2 + '        if (_attempt < _retryDelays.length) {\n',
            indent2 + '            setTimeout(function() { refreshAllBadges(_attempt + 1); }, _retryDelays[_attempt]);\n',
            indent2 + '        }\n',
            indent2 + '        return null;\n',
            indent2 + '    }\n',
            indent2 + '    return r.json();\n',
            indent2 + '})\n',
        ]
        changes.append('A2. refreshAllBadges .then(r) avec retry sur !r.ok')
    
    # Remplacer le .catch vide par un catch avec retry
    idx3 = find_line(".catch(function() {});", idx)
    if idx3 >= 0:
        indent3 = '                        '
        lines[idx3:idx3+1] = [
            indent3 + ".catch(function(err) {\n",
            indent3 + "    console.warn('refreshAllBadges erreur (essai ' + (_attempt+1) + '):', err);\n",
            indent3 + "    if (_attempt < _retryDelays.length) {\n",
            indent3 + "        setTimeout(function() { refreshAllBadges(_attempt + 1); }, _retryDelays[_attempt]);\n",
            indent3 + "    }\n",
            indent3 + "});\n",
        ]
        changes.append('A3. refreshAllBadges .catch avec retry')
else:
    changes.append('WARN A: refreshAllBadges() non trouvé')

# ═══════════════════════════════════════════════════════════
# B. RETRIES dans refreshMissionDots  
# ═══════════════════════════════════════════════════════════
idx = find_line('function refreshMissionDots()')
if idx >= 0:
    lines[idx] = lines[idx].replace('function refreshMissionDots()', 'function refreshMissionDots(_attempt)')
    indent = '                    '
    lines.insert(idx+1, indent + '_attempt = _attempt || 0;\n')
    lines.insert(idx+2, indent + 'var _mRetryDelays = [600, 2000, 5000];\n')
    changes.append('B1. refreshMissionDots signature + retryDelays')
    
    idx2 = find_line(".then(function(r) { if (!r.ok) return null; return r.json(); })", idx)
    if idx2 >= 0:
        indent2 = '                        '
        lines[idx2:idx2+1] = [
            indent2 + '.then(function(r) {\n',
            indent2 + '    if (!r.ok) {\n',
            indent2 + '        if (_attempt < _mRetryDelays.length) {\n',
            indent2 + '            setTimeout(function() { refreshMissionDots(_attempt + 1); }, _mRetryDelays[_attempt]);\n',
            indent2 + '        }\n',
            indent2 + '        return null;\n',
            indent2 + '    }\n',
            indent2 + '    return r.json();\n',
            indent2 + '})\n',
        ]
        changes.append('B2. refreshMissionDots .then(r) avec retry')
    
    # Le 2e .catch vide (après refreshMissionDots)
    idx3 = find_line(".catch(function() {});", idx)
    if idx3 >= 0:
        indent3 = '                        '
        lines[idx3:idx3+1] = [
            indent3 + ".catch(function(err) {\n",
            indent3 + "    console.warn('refreshMissionDots erreur (essai ' + (_attempt+1) + '):', err);\n",
            indent3 + "    if (_attempt < _mRetryDelays.length) {\n",
            indent3 + "        setTimeout(function() { refreshMissionDots(_attempt + 1); }, _mRetryDelays[_attempt]);\n",
            indent3 + "    }\n",
            indent3 + "});\n",
        ]
        changes.append('B3. refreshMissionDots .catch avec retry')
else:
    changes.append('WARN B: refreshMissionDots() non trouvé')

# ═══════════════════════════════════════════════════════════
# C. BFCACHE dans pageshow
# ═══════════════════════════════════════════════════════════
idx = find_line("pageshow event, persisted=")
if idx >= 0:
    # Insérer le bloc bfcache après le console.log
    indent = '                    '
    lines.insert(idx+1, indent + 'if (event.persisted) {\n')
    lines.insert(idx+2, indent + '    // bfcache : forcer rechargement complet pour badges Jinja frais\n')
    lines.insert(idx+3, indent + '    window.location.reload();\n')
    lines.insert(idx+4, indent + '    return;\n')
    lines.insert(idx+5, indent + '}\n')
    changes.append('C. pageshow bfcache reload')
else:
    changes.append('WARN C: pageshow non trouvé')

# ═══════════════════════════════════════════════════════════
# D. Supprimer appels morts dans refreshAllBadges
# ═══════════════════════════════════════════════════════════
to_remove = []
for i, l in enumerate(lines):
    stripped = l.strip()
    if stripped == 'if (counts.unread_by_sender) updateUnreadBySender(counts.unread_by_sender);':
        to_remove.append(i)
    elif stripped == 'if (counts.children_unread) updateChildrenBadges(counts.children_unread);':
        to_remove.append(i)
for i in reversed(to_remove):
    lines.pop(i)
if to_remove:
    changes.append(f'D. {len(to_remove)} appel(s) mort(s) supprimé(s) dans refreshAllBadges')

# ═══════════════════════════════════════════════════════════
# E. Supprimer CSS .avatar-notification-badge + :hover
# ═══════════════════════════════════════════════════════════
idx_start = find_line('/* Badge de notification sur l\'avatar */')
if idx_start >= 0:
    # Trouver la fin du bloc :hover (closing })
    idx_end = idx_start
    braces = 0
    found_hover = False
    for i in range(idx_start, min(idx_start + 50, len(lines))):
        if '.avatar-notification-badge:hover' in lines[i]:
            found_hover = True
        if '{' in lines[i]:
            braces += lines[i].count('{')
        if '}' in lines[i]:
            braces -= lines[i].count('}')
        if found_hover and braces <= 0:
            idx_end = i
            break
    # Supprimer les lignes
    del lines[idx_start:idx_end+1]
    changes.append(f'E. CSS .avatar-notification-badge supprimé (lignes {idx_start+1}-{idx_end+1})')
else:
    changes.append('WARN E: CSS .avatar-notification-badge non trouvé')

# ═══════════════════════════════════════════════════════════
# F. Supprimer HTML <span class="avatar-notification-badge"> (3 occurrences)
# ═══════════════════════════════════════════════════════════
# Chercher les 3 occurrences et leurs contextes Jinja
removed_html = 0
# Parcourir de la fin vers le début pour ne pas décaler les index
html_indices = []
for i, l in enumerate(lines):
    if 'class="avatar-notification-badge"' in l:
        html_indices.append(i)

for i in reversed(html_indices):
    # Vérifier si la ligne précédente est un {% if ... %} et la suivante {% endif %}
    # Ou si c'est entouré d'un commentaire + set + if/endif
    start = i
    end = i
    
    # Regarder au-dessus : commentaires et {% set %} et {% if %}
    for k in range(i-1, max(i-6, -1), -1):
        s = lines[k].strip()
        if (s.startswith('<!--') or s.startswith('{%') or s.startswith('{#') or s == ''):
            start = k
        else:
            break
    
    # Regarder en-dessous : {% endif %}
    for k in range(i+1, min(i+3, len(lines))):
        s = lines[k].strip()
        if s == '{% endif %}' or s == '':
            end = k
        else:
            break
    
    del lines[start:end+1]
    removed_html += 1

if removed_html:
    changes.append(f'F. {removed_html} HTML avatar-notification-badge supprimé(s)')
else:
    changes.append('WARN F: HTML avatar-notification-badge non trouvé')

# ═══════════════════════════════════════════════════════════
# G. Supprimer code burger dans updateUnreadBadge()
# ═══════════════════════════════════════════════════════════
idx = find_line("burger-nav-icon .notification-badge")
if idx >= 0:
    # Trouver le début du bloc (commentaire au-dessus) et la fin (fermeture forEach)
    start = idx
    for k in range(idx-1, max(idx-5, -1), -1):
        if 'menu burger' in lines[k] or 'Mettre à jour le badge dans le menu' in lines[k]:
            start = k
            break
    # Trouver la fin du forEach
    end = idx
    for k in range(idx+1, min(idx+20, len(lines))):
        if '});' in lines[k] and 'forEach' not in lines[k]:
            end = k
            break
    del lines[start:end+1]
    changes.append('G. JS burger badge code mort supprimé')
else:
    changes.append('WARN G: burger badge code non trouvé')

# ═══════════════════════════════════════════════════════════
# H. Supprimer console.logs dans updateUnreadBadge
# ═══════════════════════════════════════════════════════════
to_remove = []
for i, l in enumerate(lines):
    s = l.strip()
    if s == "console.log('updateUnreadBadge appelé avec count:', count);":
        to_remove.append(i)
    elif s == "console.log('📍 Bottom nav badge trouvé:', bottomNavBadge);":
        to_remove.append(i)
for i in reversed(to_remove):
    lines.pop(i)
if to_remove:
    changes.append(f'H. {len(to_remove)} console.log(s) supprimé(s) dans updateUnreadBadge')

# ═══════════════════════════════════════════════════════════
# I. Supprimer functions updateUnreadBySender et updateChildrenBadges
# ═══════════════════════════════════════════════════════════
for func_name in ['updateUnreadBySender', 'updateChildrenBadges']:
    # Trouver le commentaire au-dessus de la function
    idx = find_line(f'function {func_name}(')
    if idx >= 0:
        start = idx
        # Chercher le commentaire au-dessus
        for k in range(idx-1, max(idx-4, -1), -1):
            if func_name in lines[k] or 'Fonctions utilitaires badges' in lines[k]:
                start = k
        # Trouver la fin de la function (closing brace au bon niveau d'indentation)
        end = idx
        brace_count = 0
        for k in range(idx, min(idx+30, len(lines))):
            brace_count += lines[k].count('{') - lines[k].count('}')
            if brace_count <= 0 and k > idx:
                end = k
                break
        del lines[start:end+1]
        changes.append(f'I. function {func_name}() supprimée')
    else:
        changes.append(f'WARN I: function {func_name}() non trouvée')

# ═══════════════════════════════════════════════════════════
# J. Supprimer tous les APPELS à updateChildrenBadges() et updateUnreadBySender()
# ═══════════════════════════════════════════════════════════
to_remove = []
for i, l in enumerate(lines):
    s = l.strip()
    if s.startswith('updateChildrenBadges(') or s.startswith('updateUnreadBySender('):
        to_remove.append(i)
        # Aussi supprimer un éventuel commentaire console.log ou condition if au-dessus
        if i > 0:
            prev = lines[i-1].strip()
            if prev.startswith('console.log') and ('enfants' in prev or 'badges' in prev.lower()):
                to_remove.append(i-1)
    # Lignes conditionnelles comme: if (data.unread_by_sender) { ... }
    if 'if (counts.unread_by_sender)' in s or 'if (data.unread_by_sender)' in s:
        if 'updateUnreadBySender' in s:
            to_remove.append(i)
    if 'if (counts.children_unread)' in s or 'if (data.children_unread)' in s:
        if 'updateChildrenBadges' in s:
            to_remove.append(i)

to_remove = sorted(set(to_remove), reverse=True)
for i in to_remove:
    lines.pop(i)
if to_remove:
    changes.append(f'J. {len(to_remove)} appel(s)/ligne(s) updateChildrenBadges/updateUnreadBySender supprimé(s)')

# ═══════════════════════════════════════════════════════════
# K. Supprimer socket.on('unread_by_sender_update') handler
# ═══════════════════════════════════════════════════════════
idx = find_line("socket.on('unread_by_sender_update'")
if idx >= 0:
    start = idx
    # Chercher le commentaire au-dessus
    for k in range(idx-1, max(idx-3, -1), -1):
        if 'badges sur les avatars' in lines[k] or 'Écouter les mises' in lines[k]:
            start = k
    # Trouver la fermeture });
    end = idx
    brace_count = 0
    for k in range(idx, min(idx+20, len(lines))):
        brace_count += lines[k].count('{') - lines[k].count('}')
        if brace_count <= 0 and k > idx:
            end = k
            break
    del lines[start:end+1]
    changes.append('K. socket.on(unread_by_sender_update) handler supprimé')
else:
    changes.append('INFO K: socket.on(unread_by_sender_update) déjà supprimé')

# ═══════════════════════════════════════════════════════════
# L. Supprimer socket.on('badge_update') handler
# ═══════════════════════════════════════════════════════════
idx = find_line("socket.on('badge_update'")
if idx >= 0:
    start = idx
    for k in range(idx-1, max(idx-3, -1), -1):
        if 'Pastille enfant' in lines[k]:
            start = k
    end = idx
    brace_count = 0
    for k in range(idx, min(idx+15, len(lines))):
        brace_count += lines[k].count('{') - lines[k].count('}')
        if brace_count <= 0 and k > idx:
            end = k
            break
    del lines[start:end+1]
    changes.append('L. socket.on(badge_update) handler supprimé')
else:
    changes.append('INFO L: socket.on(badge_update) déjà supprimé')

# ═══════════════════════════════════════════════════════════
# M. Supprimer socket.on('unread_sent_to_update') handler
# ═══════════════════════════════════════════════════════════
idx = find_line("socket.on('unread_sent_to_update'")
if idx >= 0:
    start = idx
    for k in range(idx-1, max(idx-3, -1), -1):
        if 'avatar enfant' in lines[k] or 'Pastille sur' in lines[k]:
            start = k
    end = idx
    brace_count = 0
    for k in range(idx, min(idx+25, len(lines))):
        brace_count += lines[k].count('{') - lines[k].count('}')
        if brace_count <= 0 and k > idx:
            end = k
            break
    del lines[start:end+1]
    changes.append('M. socket.on(unread_sent_to_update) handler supprimé')
else:
    changes.append('INFO M: socket.on(unread_sent_to_update) déjà supprimé')

# ═══════════════════════════════════════════════════════════
# ÉCRITURE
# ═══════════════════════════════════════════════════════════
with open(FILE, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'\n{"="*60}')
print(f'Modifications terminées : {len(changes)} opérations')
print(f'Lignes : 6887 → {len(lines)}')
print(f'{"="*60}')
for c in changes:
    status = '✅' if not c.startswith('WARN') else '⚠️ '
    if c.startswith('INFO'):
        status = 'ℹ️ '
    print(f'  {status} {c}')

# Vérification finale
src = ''.join(lines)
print(f'\nVérification finale :')
for kw in ['avatar-notification-badge', 'updateUnreadBySender', 'updateChildrenBadges',
           'burger-nav-icon .notification-badge']:
    cnt = src.count(kw)
    print(f'  {"✅" if cnt == 0 else "⚠️  " + str(cnt)} {kw}')

# Vérifier les fonctions de retries
print(f'\nFonctions modifiées :')
print(f'  {"✅" if "refreshAllBadges(_attempt)" in src else "❌"} refreshAllBadges avec retries')
print(f'  {"✅" if "refreshMissionDots(_attempt)" in src else "❌"} refreshMissionDots avec retries')
print(f'  {"✅" if "event.persisted" in src else "❌"} pageshow bfcache handling')
