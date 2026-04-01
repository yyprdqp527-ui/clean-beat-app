#!/usr/bin/env python3
"""Nettoyage complet du code mort des anciens badges avatars dans menu.html.

Supprime :
1. CSS .avatar-notification-badge + :hover
2. HTML <span class="avatar-notification-badge"> (3 occurrences)
3. JS burger badge code mort dans updateUnreadBadge()
4. JS console.log excessifs dans updateUnreadBadge()
5. JS function updateUnreadBySender() entière
6. JS function updateChildrenBadges() entière
7. JS appels updateChildrenBadges() dans socket.io handlers (4 occurrences)
8. JS appels updateUnreadBySender() dans socket.io handlers (3 occurrences)
9. JS socket.on('unread_sent_to_update') handler entier (utilise avatar-notification-badge)
10. JS socket.on('badge_update') handler entier (appelle updateChildrenBadges)
11. JS socket.on('unread_by_sender_update') handler entier (appelle updateUnreadBySender)
"""
import re, sys

FILE = 'templates/menu.html'

with open(FILE, 'r', encoding='utf-8') as f:
    src = f.read()

original_len = len(src)
changes = []

# ─────────────────────────────────────────────────────────
# 1. CSS : supprimer .avatar-notification-badge { ... }
# ─────────────────────────────────────────────────────────
pat_css = r'/\* Badge de notification sur l\'avatar \*/\s*\.avatar-notification-badge \{[^}]+\}\s*\.avatar-notification-badge:hover \{[^}]+\}'
m = re.search(pat_css, src)
if m:
    src = src[:m.start()] + src[m.end():]
    changes.append('1. CSS .avatar-notification-badge supprimé')
else:
    changes.append('WARN 1: CSS .avatar-notification-badge non trouvé')

# ─────────────────────────────────────────────────────────
# 2. HTML : supprimer les 3 <span class="avatar-notification-badge"...>
#    Chaque span est sur une seule ligne, parfois précédé de Jinja {% if %}
# ─────────────────────────────────────────────────────────

# 2a. Premier span (L2786 environ) — entouré de {% if current_user_unread > 0 %} ... {% endif %}
pat_html1 = r'<!-- Badge pour les messages REÇUS par l\'utilisateur connecté -->\s*\n\s*\{%[^%]*current_user_unread[^%]*%\}\s*\n\s*\{%\s*if\s+current_user_unread\s*>\s*0\s*%\}\s*\n\s*<span class="avatar-notification-badge"[^>]*>[^<]*</span>\s*\n\s*\{%\s*endif\s*%\}'
m = re.search(pat_html1, src)
if m:
    src = src[:m.start()] + src[m.end():]
    changes.append('2a. HTML avatar-notification-badge (current_user) supprimé')
else:
    changes.append('WARN 2a: HTML current_user badge non trouvé')

# 2b. Deuxième span (L2846 environ) — juste le <span> line
count_before = src.count('avatar-notification-badge')
pat_html2 = r'<span class="avatar-notification-badge" data-recipient="\{\{ p2\.email \}\}"[^>]*>[^<]*</span>'
src = re.sub(pat_html2, '', src)
count_after = src.count('avatar-notification-badge')
if count_after < count_before:
    changes.append('2b. HTML avatar-notification-badge (p2) supprimé')
else:
    changes.append('WARN 2b: HTML p2 badge non trouvé')

# 2c. Troisième span (L2901 environ) — juste le <span> line
count_before = src.count('avatar-notification-badge')
pat_html3 = r'<span class="avatar-notification-badge" data-recipient="\{\{ p\.email \}\}"[^>]*>[^<]*</span>'
src = re.sub(pat_html3, '', src)
count_after = src.count('avatar-notification-badge')
if count_after < count_before:
    changes.append('2c. HTML avatar-notification-badge (p) supprimé')
else:
    changes.append('WARN 2c: HTML p badge non trouvé')

# ─────────────────────────────────────────────────────────
# 3. JS : Nettoyer updateUnreadBadge() — supprimer burger badge + console.logs
# ─────────────────────────────────────────────────────────
# Remplacer la function entière par une version clean
old_fn = r"""function updateUnreadBadge\(count\) \{[^}]*?//\s*💬 Mettre à jour le badge du bouton Messages"""
# Plus simple : chercher le bloc entre "function updateUnreadBadge(count)" et la fermeture "}"
# On va utiliser une approche par remplacement de texte exact

# Burger badge block
burger_pat = r"//\s*.*Mettre à jour le badge dans le menu burger.*\n\s*const burgerBadges = document\.querySelectorAll\('\.burger-nav-icon \.notification-badge'\);\s*\n\s*console\.log\('Badges burger trouvés:', burgerBadges\.length\);\s*\n\s*burgerBadges\.forEach\(badge => \{[^}]*?\}\);\s*\n"
m = re.search(burger_pat, src, re.DOTALL)
if m:
    src = src[:m.start()] + src[m.end():]
    changes.append('3a. JS burger badge code mort supprimé')
else:
    changes.append('WARN 3a: JS burger badge code non trouvé')

# Console.logs in updateUnreadBadge
for clog in [
    r"console\.log\('updateUnreadBadge appelé avec count:', count\);\s*\n",
    r"\s*console\.log\('📍 Bottom nav badge trouvé:', bottomNavBadge\);\s*\n",
]:
    m = re.search(clog, src)
    if m:
        src = src[:m.start()] + '\n' + src[m.end():]
        changes.append(f'3b. console.log supprimé dans updateUnreadBadge')

# Note: badge del dans updateUnreadBadge — ne pas supprimer les lignes du bottom nav badge (fonctionnel)

# ─────────────────────────────────────────────────────────
# 4. JS : Supprimer le commentaire + function updateUnreadBySender() entière
# ─────────────────────────────────────────────────────────
fn_pat = r"// ✅ Fonctions utilitaires badges \(pastilles avatars\)[^\n]*\n\s*// updateUnreadBySender:[^\n]*\n\s*function updateUnreadBySender\(senderMap\) \{.*?\n\s*\}"
m = re.search(fn_pat, src, re.DOTALL)
if m:
    src = src[:m.start()] + src[m.end():]
    changes.append('4. JS updateUnreadBySender() supprimé')
else:
    changes.append('WARN 4: JS updateUnreadBySender() non trouvé')

# ─────────────────────────────────────────────────────────
# 5. JS : Supprimer le commentaire + function updateChildrenBadges() entière
# ─────────────────────────────────────────────────────────
fn_pat2 = r"// updateChildrenBadges:[^\n]*\n\s*function updateChildrenBadges\(childMap\) \{.*?\n\s*\}"
m = re.search(fn_pat2, src, re.DOTALL)
if m:
    src = src[:m.start()] + src[m.end():]
    changes.append('5. JS updateChildrenBadges() supprimé')
else:
    changes.append('WARN 5: JS updateChildrenBadges() non trouvé')

# ─────────────────────────────────────────────────────────
# 6. JS : Supprimer tous les appels updateChildrenBadges(...) restants
# ─────────────────────────────────────────────────────────
count_before = src.count('updateChildrenBadges')
# Supprimer les lignes contenant updateChildrenBadges et le contexte commentaire
src = re.sub(r'\s*(?:console\.log\([^)]*\);\s*\n)?\s*updateChildrenBadges\([^)]*\);\s*\n', '\n', src)
count_after = src.count('updateChildrenBadges')
if count_after < count_before:
    changes.append(f'6. {count_before - count_after} appel(s) updateChildrenBadges supprimé(s)')
else:
    changes.append('WARN 6: Aucun appel updateChildrenBadges trouvé')

# ─────────────────────────────────────────────────────────
# 7. JS : Supprimer tous les appels updateUnreadBySender(...) restants
# ─────────────────────────────────────────────────────────
count_before = src.count('updateUnreadBySender')
src = re.sub(r'\s*updateUnreadBySender\([^)]*\);\s*\n', '\n', src)
count_after = src.count('updateUnreadBySender')
if count_after < count_before:
    changes.append(f'7. {count_before - count_after} appel(s) updateUnreadBySender supprimé(s)')
else:
    changes.append('WARN 7: Aucun appel updateUnreadBySender trouvé')

# ─────────────────────────────────────────────────────────
# 8. JS : Supprimer socket.on('unread_by_sender_update') handler entier
# ─────────────────────────────────────────────────────────
pat_ws1 = r"// Écouter les mises à jour des badges sur les avatars\s*\n\s*socket\.on\('unread_by_sender_update'[^}]*\}\);\s*\n"
m = re.search(pat_ws1, src, re.DOTALL)
if m:
    src = src[:m.start()] + src[m.end():]
    changes.append('8. JS socket.on(unread_by_sender_update) handler supprimé')
else:
    changes.append('WARN 8: socket.on(unread_by_sender_update) non trouvé')

# ─────────────────────────────────────────────────────────
# 9. JS : Supprimer socket.on('badge_update') handler entier
# ─────────────────────────────────────────────────────────
pat_ws2 = r"//\s*.*Pastille enfant mise à jour quand.*\n\s*socket\.on\('badge_update'[^}]*\}\);\s*\n"
m = re.search(pat_ws2, src, re.DOTALL)
if m:
    src = src[:m.start()] + src[m.end():]
    changes.append('9. JS socket.on(badge_update) handler supprimé')
else:
    changes.append('WARN 9: socket.on(badge_update) non trouvé')

# ─────────────────────────────────────────────────────────
# 10. JS : Supprimer socket.on('unread_sent_to_update') handler entier
# ─────────────────────────────────────────────────────────
pat_ws3 = r"//\s*.*Pastille sur avatar enfant quand message envoyé.*\n\s*socket\.on\('unread_sent_to_update'.*?\}\);\s*\n"
m = re.search(pat_ws3, src, re.DOTALL)
if m:
    src = src[:m.start()] + src[m.end():]
    changes.append('10. JS socket.on(unread_sent_to_update) handler supprimé')
else:
    changes.append('WARN 10: socket.on(unread_sent_to_update) non trouvé')

# ─────────────────────────────────────────────────────────
# 11. Nettoyage final : supprimer les lignes vides consécutives (> 2)
# ─────────────────────────────────────────────────────────
src = re.sub(r'\n{4,}', '\n\n\n', src)

# ─────────────────────────────────────────────────────────
# Écriture
# ─────────────────────────────────────────────────────────
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(src)

print(f'\n{"="*60}')
print(f'Nettoyage terminé : {len(changes)} opérations')
print(f'Taille : {original_len} → {len(src)} ({original_len - len(src)} chars supprimés)')
print(f'{"="*60}')
for c in changes:
    print(f'  {"✅" if not c.startswith("WARN") else "⚠️ "} {c}')

# Vérification finale
remaining = sum(1 for kw in ['avatar-notification-badge', 'updateUnreadBySender', 'updateChildrenBadges',
                               'burger-nav-icon .notification-badge']
                if kw in src)
if remaining:
    print(f'\n⚠️  {remaining} mot-clé(s) encore présent(s) :')
    for kw in ['avatar-notification-badge', 'updateUnreadBySender', 'updateChildrenBadges',
               'burger-nav-icon .notification-badge']:
        cnt = src.count(kw)
        if cnt:
            print(f'    {kw}: {cnt} occurrence(s)')
else:
    print('\n✅ TOUT LE CODE MORT EST SUPPRIMÉ')
