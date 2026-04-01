#!/usr/bin/env python3
"""
Fix complet : pastilles absentes au premier chargement + nettoyage code mort pills.

CAUSES RACINES:
1. refreshAllBadges() et refreshMissionDots() n'ont AUCUN retry quand le fetch échoue
   → sur iOS/PWA, le réseau est souvent indisponible aux premières secondes
2. pageshow ne traite pas le bfcache (event.persisted=true) → page stale restaurée
3. L'IIFE pré-affichage Jinja fonctionne pour les room cards mais ne peut PAS 
   re-appliquer au DOMContentLoaded pour les éléments nav (qui sont après le script)
4. Code mort des anciennes pills sur avatars (CSS + JS) → à supprimer

CORRECTIONS:
A. Ajouter retries avec backoff dans refreshAllBadges() et refreshMissionDots()
B. Forcer location.reload() dans pageshow quand bfcache détecté
C. Ajouter un DOMContentLoaded qui applique les valeurs Jinja aux badges nav basse
D. Supprimer code mort : .notification-badge CSS, .avatar-notification-badge CSS,
   applyAvatarUnreadBadges(), burger-nav-icon .notification-badge dans updateUnreadBadge(),
   updateUnreadBySender(), updateUnreadSentTo()
"""

import re

filepath = 'templates/menu.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

original_len = len(content)
changes = []

# ================================================================
# A. Remplacer refreshAllBadges() par version avec retries
# ================================================================
old_refresh = 'function refreshAllBadges() {\n                    fetch(\'/api/unread_counts\', { cache: \'no-store\', credentials: \'same-origin\' })'
if old_refresh in content:
    new_refresh = 'function refreshAllBadges(_attempt) {\n                    _attempt = _attempt || 0;\n                    var _retryDelays = [500, 1500, 4000];\n                    fetch(\'/api/unread_counts\', { cache: \'no-store\', credentials: \'same-origin\' })'
    content = content.replace(old_refresh, new_refresh, 1)
    changes.append("A1: refreshAllBadges - ajout param _attempt + retryDelays")
else:
    print("WARN: refreshAllBadges signature non trouvée")

# Ajouter retry dans le .catch de refreshAllBadges
old_catch_all = ".catch(function() {});\n                }\n\n                // " + chr(0x2500)*2
if old_catch_all in content:
    new_catch_all = """.catch(function(err) {
                            console.warn('refreshAllBadges erreur (essai ' + (_attempt+1) + '):', err);
                            if (_attempt < _retryDelays.length) {
                                setTimeout(function() { refreshAllBadges(_attempt + 1); }, _retryDelays[_attempt]);
                            }
                        });
                }

                // """ + chr(0x2500)*2
    content = content.replace(old_catch_all, new_catch_all, 1)
    changes.append("A2: refreshAllBadges - retry dans .catch")

# Ajouter retry dans le !r.ok de refreshAllBadges
old_not_ok = ".then(function(r) { if (!r.ok) return null; return r.json(); })\n                        .then(function(counts) {\n                            if (!counts || counts.error) return;"
if old_not_ok in content:
    new_not_ok = """.then(function(r) {
                            if (!r.ok) {
                                if (_attempt < _retryDelays.length) {
                                    setTimeout(function() { refreshAllBadges(_attempt + 1); }, _retryDelays[_attempt]);
                                }
                                return null;
                            }
                            return r.json();
                        })
                        .then(function(counts) {
                            if (!counts || counts.error) return;"""
    content = content.replace(old_not_ok, new_not_ok, 1)
    changes.append("A3: refreshAllBadges - retry si !r.ok")
else:
    print("WARN: !r.ok pattern non trouvé dans refreshAllBadges")

# ================================================================
# B. Remplacer refreshMissionDots() par version avec retries
# ================================================================
old_mission = 'function refreshMissionDots() {\n                    fetch(\'/api/rooms_with_missions\', { cache: \'no-store\', credentials: \'same-origin\' })'
if old_mission in content:
    new_mission = 'function refreshMissionDots(_attempt) {\n                    _attempt = _attempt || 0;\n                    var _mRetryDelays = [600, 2000, 5000];\n                    fetch(\'/api/rooms_with_missions\', { cache: \'no-store\', credentials: \'same-origin\' })'
    content = content.replace(old_mission, new_mission, 1)
    changes.append("B1: refreshMissionDots - ajout param _attempt + retries")
else:
    print("WARN: refreshMissionDots signature non trouvée")

# Chercher et remplacer le .then(.ok) et .catch de refreshMissionDots
# Le pattern est différent de refreshAllBadges - cherchons le bon
old_mission_ok = ".then(function(r) { if (!r.ok) return null; return r.json(); })\n                        .then(function(data) {\n                            if (!data || !data.rooms) return;"
# Il y en a possiblement 2 (une dans refreshAllBadges déjà remplacée, une dans refreshMissionDots)
# On remplace la 2ème occurrence
count_mission_ok = content.count(old_mission_ok)
if count_mission_ok >= 1:
    # Remplacer la dernière occurrence (refreshMissionDots est après refreshAllBadges)
    idx = content.rfind(old_mission_ok)
    new_mission_ok = """.then(function(r) {
                            if (!r.ok) {
                                if (_attempt < _mRetryDelays.length) {
                                    setTimeout(function() { refreshMissionDots(_attempt + 1); }, _mRetryDelays[_attempt]);
                                }
                                return null;
                            }
                            return r.json();
                        })
                        .then(function(data) {
                            if (!data || !data.rooms) return;"""
    content = content[:idx] + new_mission_ok + content[idx + len(old_mission_ok):]
    changes.append("B2: refreshMissionDots - retry si !r.ok")
else:
    print(f"WARN: refreshMissionDots !r.ok pattern non trouvé (count={count_mission_ok})")

# Ajouter retry dans le .catch de refreshMissionDots (dernière occurrence de .catch(function() {});)
old_mission_catch = "                        .catch(function() {});\n                }\n\n                // Exposer globalement"
if old_mission_catch in content:
    new_mission_catch = """                        .catch(function(err) {
                            console.warn('refreshMissionDots erreur (essai ' + (_attempt+1) + '):', err);
                            if (_attempt < _mRetryDelays.length) {
                                setTimeout(function() { refreshMissionDots(_attempt + 1); }, _mRetryDelays[_attempt]);
                            }
                        });
                }

                // Exposer globalement"""
    content = content.replace(old_mission_catch, new_mission_catch, 1)
    changes.append("B3: refreshMissionDots - retry dans .catch")
else:
    print("WARN: refreshMissionDots .catch pattern non trouvé")

# ================================================================
# C. Corriger le pageshow pour traiter le bfcache
# ================================================================
old_pageshow = """window.addEventListener('pageshow', function(event) {
                    console.log('🔄 pageshow event, persisted=' + event.persisted);
                    window.refreshAllBadges();
                    if (window.refreshMissionDots) window.refreshMissionDots();
                    if (typeof updatePlayersPointsMenu === 'function') updatePlayersPointsMenu();
                });"""
if old_pageshow in content:
    new_pageshow = """window.addEventListener('pageshow', function(event) {
                    console.log('🔄 pageshow event, persisted=' + event.persisted);
                    if (event.persisted) {
                        // bfcache : forcer rechargement complet pour badges Jinja frais
                        window.location.reload();
                        return;
                    }
                    window.refreshAllBadges();
                    if (window.refreshMissionDots) window.refreshMissionDots();
                    if (typeof updatePlayersPointsMenu === 'function') updatePlayersPointsMenu();
                });"""
    content = content.replace(old_pageshow, new_pageshow, 1)
    changes.append("C: pageshow - ajout location.reload() pour bfcache")
else:
    print("WARN: pageshow handler non trouvé")

# ================================================================
# D. Supprimer .notification-badge CSS (code mort - aucun élément ne l'utilise)
# ================================================================
old_notif_css = """/* Badge de notification */
        .notification-badge {"""
idx_css = content.find(old_notif_css)
if idx_css >= 0:
    # Trouver la fin du bloc CSS (prochaine accolade fermante + saut de ligne)
    end_css = content.find('\n        \n', idx_css)
    if end_css < 0:
        end_css = content.find('\n        /*', idx_css + 50)
    if end_css > idx_css:
        removed_css = content[idx_css:end_css]
        content = content[:idx_css] + content[end_css:]
        changes.append(f"D1: Supprimé CSS .notification-badge ({len(removed_css)} chars)")

# ================================================================
# E. Supprimer .avatar-notification-badge CSS (display:none!important, code mort)
# ================================================================
old_avatar_css = """/* Badge de notification sur l'avatar */
        .avatar-notification-badge {"""
idx_css2 = content.find(old_avatar_css)
if idx_css2 >= 0:
    # Trouver la fin du bloc (inclut :hover)
    hover_end = content.find('.avatar-emoji-badge', idx_css2)
    if hover_end > idx_css2:
        # Remonter pour trouver le début du commentaire précédent
        line_start = content.rfind('\n', 0, hover_end)
        while line_start > idx_css2 and content[line_start:line_start+10].strip() == '':
            line_start = content.rfind('\n', 0, line_start)
        removed_css2 = content[idx_css2:line_start + 1]
        content = content[:idx_css2] + content[line_start + 1:]
        changes.append(f"E: Supprimé CSS .avatar-notification-badge + :hover ({len(removed_css2)} chars)")

# ================================================================
# F. Nettoyer updateUnreadBadge : supprimer la partie burger-nav-icon .notification-badge
# ================================================================
old_burger_badge = """                    // Mettre à jour le badge dans le menu burger (total des messages)
                    const burgerBadges = document.querySelectorAll('.burger-nav-icon .notification-badge');
                    burgerBadges.forEach(badge => {
                        if (count > 0) {
                            badge.textContent = count < 100 ? count : '99+';
                            badge.style.display = 'flex';
                        } else {
                            badge.style.display = 'none';
                        }
                    });
                    
                    // 💬"""
if old_burger_badge in content:
    content = content.replace(old_burger_badge, '                    // 💬', 1)
    changes.append("F: Supprimé burger .notification-badge dans updateUnreadBadge")
else:
    print("WARN: burger badge code non trouvé")

# ================================================================
# G. Supprimer applyAvatarUnreadBadges et les fonctions associées
# ================================================================
old_avatar_js = """                //  Masquer tous les badges d'avatars (désormais inutilisés)
                function applyAvatarUnreadBadges() {
                    // ❌ Les badges d'avatars sont désormais désactivés
                    // Les notifications sont affichées uniquement dans le menu de navigation fixe
                    document.querySelectorAll('.avatar-notification-badge').forEach(badge => {
                        badge.style.display = 'none';
                    });
                }

                // Compat: conserver ce nom appelé ailleurs, mais stocker dans le bon cache
                function updateUnreadSentTo(unreadSentTo) {
                    window.__unreadSentTo = unreadSentTo || {};
                    applyAvatarUnreadBadges();
                }

                function updateUnreadBySender(unreadBySender) {
                    window.__unreadBySender = unreadBySender || {};
                    applyAvatarUnreadBadges();
                }"""
if old_avatar_js in content:
    content = content.replace(old_avatar_js, '', 1)
    changes.append("G: Supprimé applyAvatarUnreadBadges + updateUnreadSentTo + updateUnreadBySender")
else:
    print("WARN: applyAvatarUnreadBadges bloc non trouvé")

# ================================================================
# H. Supprimer les appels à updateUnreadBySender/updateUnreadSentTo dans refreshAllBadges
# ================================================================
for func_call in ['if (counts.unread_by_sender) updateUnreadBySender(counts.unread_by_sender);',
                  'if (counts.children_unread) updateChildrenBadges(counts.children_unread);']:
    if func_call in content:
        content = content.replace(func_call, '', 1)
        changes.append(f"H: Supprimé appel {func_call[:50]}...")

# ================================================================
# I. Supprimer window.__unreadBySender / __unreadSentTo
# ================================================================
old_caches = """                // Caches locaux des compteurs pour fusionner les deux sens de lecture
                window.__unreadBySender = window.__unreadBySender || {};
                window.__unreadSentTo = window.__unreadSentTo || {};
"""
if old_caches in content:
    content = content.replace(old_caches, '', 1)
    changes.append("I: Supprimé caches __unreadBySender/__unreadSentTo")

# ================================================================
# Résultat
# ================================================================
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n{'='*60}")
print(f"Taille: {original_len} → {len(content)} ({len(content) - original_len:+d} chars)")
print(f"Modifications: {len(changes)}")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
print(f"{'='*60}")
