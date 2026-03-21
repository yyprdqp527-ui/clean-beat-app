#!/usr/bin/env python3
"""
Script pour déplacer les notifications de messages des avatars vers le menu de navigation fixe en bas.
"""

import re

# Lire le fichier
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Modification 1: Supprimer les badges HTML sur les avatars joueurs
# Joueur 2
pattern1 = r'(</div>\s*<!-- Badge des messages non lus de ce joueur \(reçus par vous\) -->\s*{% set p2_unread.+?</span>\s*)(\n\s*<div class="vbar simple")'
replacement1 = r'\2'
content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

# Autres joueurs  
pattern2 = r'(</div>\s*<!-- Badge des messages non lus de ce joueur \(reçus par vous\) -->\s*{% set p_unread.+?</span>\s*)(\n\s*<div class="vbar simple")'
replacement2 = r'\2'
content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)

# Joueur 1 (utilisateur actuel) - commentaire seulement
pattern3 = r'(\n\s*<!-- Badge désactivé - notifications désormais dans le menu de navigation fixe -->\s*\n)'
replacement3 = r'\n'
content = re.sub(pattern3, replacement3, content)

# Modification 2: Modifier applyAvatarUnreadBadges() pour masquer tous les badges
old_func = '''                function applyAvatarUnreadBadges() {
                    // Cette fonction n'est plus nécessaire car updateUnreadBadge gère déjà la pastille sur l'avatar de l'utilisateur actuel
                    // On la garde vide pour compatibilité avec les appels existants
                }'''

new_func = '''                function applyAvatarUnreadBadges() {
                    // ❌ Les badges d'avatars sont désormais désactivés
                    // Les notifications sont affichées uniquement dans le menu de navigation fixe
                    document.querySelectorAll('.avatar-notification-badge').forEach(badge => {
                        badge.style.display = 'none';
                    });
                }'''

content = content.replace(old_func, new_func)

# Modification 3: Modifier refreshAllBadges() pour inclure les enfants
old_refresh = '''                function refreshAllBadges() {
                    console.log('🔄 Rafraîchissement des badges...');
                    fetch('/api/unread_counts', { cache: 'no-store' })
                        .then(response => response.json())
                        .then(counts => {
                            console.log('📊 Compteurs reçus de l\\'API:', counts);
                            if (counts.unread_received !== undefined) {
                                console.log('🔔 Mise à jour badge avec count:', counts.unread_received);
                                updateUnreadBadge(counts.unread_received);
                            }'''

new_refresh = '''                function refreshAllBadges() {
                    console.log('🔄 Rafraîchissement des badges...');
                    fetch('/api/unread_counts', { cache: 'no-store' })
                        .then(response => response.json())
                        .then(counts => {
                            console.log('📊 Compteurs reçus de l\\'API:', counts);
                            // 💬 Badge messages du menu en bas : inclut les messages des enfants
                            let totalMessages = counts.unread_received || 0;
                            if (counts.children_unread) {
                                for (const email in counts.children_unread) {
                                    totalMessages += counts.children_unread[email] || 0;
                                }
                            }
                            if (counts.unread_received !== undefined) {
                                console.log('🔔 Mise à jour badge avec count:', totalMessages);
                                updateUnreadBadge(totalMessages);
                            }'''

content = content.replace(old_refresh, new_refresh)

# Modification 4: Simplifier les WebSocket listeners
old_ws1 = '''                        socket.on('new_message_notification', function(data) {
                            console.log('💬 WebSocket: Nouveau message reçu', data);
                            
                            // Si l'utilisateur actuel est le DESTINATAIRE : mettre à jour son propre badge
                            if (data.recipient_email === userEmail) {
                                updateUnreadBadge(data.unread_count);
                                updateAppBadge(data.unread_count);
                                
                                // 🔔 Jouer le son de notification
                                playMessageSound();
                                
                                // Afficher une notification toast (optionnel)
                                if (typeof showToast === 'function') {
                                    showToast(\`💬 Nouveau message de \${data.sender}\`);
                                }
                            }
                            
                            // Mettre à jour les badges sur les avatars des autres joueurs (messages envoyés par vous)
                            if (data.unread_by_sender) {
                                updateUnreadBySender(data.unread_by_sender);
                            }
                            if (data.unread_sent_to) {
                                updateUnreadSentTo(data.unread_sent_to);
                            }
                        });'''

new_ws1 = '''                        socket.on('new_message_notification', function(data) {
                            console.log('💬 WebSocket: Nouveau message reçu', data);
                            
                            // Si l'utilisateur actuel est le DESTINATAIRE : recharger tous les badges (inclut enfants)
                            if (data.recipient_email === userEmail) {
                                refreshAllBadges();
                                
                                // 🔔 Jouer le son de notification
                                playMessageSound();
                                
                                // Afficher une notification toast (optionnel)
                                if (typeof showToast === 'function') {
                                    showToast(\`💬 Nouveau message de \${data.sender}\`);
                                }
                            }
                        });'''

content = content.replace(old_ws1, new_ws1)

old_ws2 = '''                        // Écouter les mises à jour du compteur de messages non lus
                        socket.on('unread_count_update', function(data) {
                            console.log('💬 WebSocket: Compteur messages non lus mis à jour', data);
                            if (data.user_email === userEmail) {
                                updateUnreadBadge(data.count);
                                // Mettre à jour les badges sur les avatars des autres joueurs
                                if (data.unread_by_sender) {
                                    updateUnreadBySender(data.unread_by_sender);
                                }
                                if (data.unread_sent_to) {
                                    updateUnreadSentTo(data.unread_sent_to);
                                }
                            }
                        });'''

new_ws2 = '''                        // Écouter les mises à jour du compteur de messages non lus
                        socket.on('unread_count_update', function(data) {
                            console.log('💬 WebSocket: Compteur messages non lus mis à jour', data);
                            if (data.user_email === userEmail) {
                                refreshAllBadges();
                            }
                        });'''

content = content.replace(old_ws2, new_ws2)

old_ws3 = '''                        // 🔌 Synchroniser la liste des messages pour tous les utilisateurs
                        socket.on('messages_list_update', function(data) {
                            console.log('📬 WebSocket Menu: Mise à jour de la liste des messages', data);
                            
                            // Recharger les compteurs de messages pour rafraîchir TOUS les badges
                            fetch('/api/unread_counts', { cache: 'no-store' })
                                .then(response => response.json())
                                .then(counts => {
                                    if (counts.unread_received !== undefined) {
                                        updateUnreadBadge(counts.unread_received);
                                    }
                                    if (counts.unread_by_sender) {
                                        updateUnreadBySender(counts.unread_by_sender);
                                    }
                                    if (counts.unread_sent_to) {
                                        updateUnreadSentTo(counts.unread_sent_to);
                                    }
                                    // Pills baby / mission / courses
                                    updatePill('pill-baby', 'pill-baby-count', counts.unread_baby || 0);
                                    // Badge nav "Liste de courses"
                                    updateCoursesNavBadge(counts.courses_pending_count || 0);
                                    // Badge icône PWA
                                    var total = (counts.unread_received || 0) + (counts.unread_baby || 0);
                                    updateAppBadge(total);
                                    console.log('✅ Badges mis à jour via API');
                                })
                                .catch(error => console.error('❌ Erreur rechargement badges:', error));
                        });'''

new_ws3 = '''                        // 🔌 Synchroniser la liste des messages pour tous les utilisateurs
                        socket.on('messages_list_update', function(data) {
                            console.log('📬 WebSocket Menu: Mise à jour de la liste des messages', data);
                            refreshAllBadges();
                        });'''

content = content.replace(old_ws3, new_ws3)

old_ws4 = '''                        // 🔔 Écouter quand un utilisateur a marqué tous ses messages comme lus
                        socket.on('all_messages_read', function(data) {
                            console.log('✅ WebSocket: Messages marqués comme lus', data);
                            if (data.reader_email === userEmail) {
                                updateUnreadBadge(0);
                            }
                        });'''

new_ws4 = '''                        // 🔔 Écouter quand un utilisateur a marqué tous ses messages comme lus
                        socket.on('all_messages_read', function(data) {
                            console.log('✅ WebSocket: Messages marqués comme lus', data);
                            if (data.reader_email === userEmail) {
                                refreshAllBadges();
                            }
                        });'''

content = content.replace(old_ws4, new_ws4)

# Écrire le fichier modifié
with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Modifications appliquées avec succès!")
print("- Badges d'avatars supprimés du HTML")
print("- applyAvatarUnreadBadges() masque tous les anciens badges")
print("- refreshAllBadges() inclut les messages des enfants")
print("- WebSocket listeners simplifiés")
