#!/usr/bin/env python3
"""Restore Handler A to original + fix Handler B malus to use original flames"""
import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# === 1) Replace HANDLER A entirely (from "// === ANIMATION GAGNANT" to the matching "})();") ===
# Find the IIFE block
handler_a_pattern = r'(                    // === ANIMATION GAGNANT APRÈS VALIDATION DE TÂCHE ===\n                    \(function\(\) \{.*?\n                    \}\)\(\);)'
match_a = re.search(handler_a_pattern, content, re.DOTALL)
if not match_a:
    print("ERROR: Could not find Handler A")
    exit(1)

print(f"Found Handler A at positions {match_a.start()}-{match_a.end()}")

handler_a_new = """                    // === ANIMATION GAGNANT APRES VALIDATION DE TACHE ===
                    (function() {
                        var params = new URLSearchParams(window.location.search);
                        var pts = params.get('pts');
                        var ts = params.get('ts');
                        var who = params.get('who');
                        var whon = params.get('whon');
                        
                        if (pts && ts) {
                            var ptsNum = parseInt(pts);
                            setTimeout(function() {
                                // Cibler l'avatar du beneficiaire si fourni, sinon le joueur courant
                                var targetWrapper = null;
                                if (who) {
                                    targetWrapper = document.querySelector('.avatar-square-wrapper[data-player-email="' + who + '"]');
                                }
                                if (!targetWrapper && whon) {
                                    targetWrapper = document.querySelector('.avatar-square-wrapper[title="' + whon + '"]');
                                }
                                if (!targetWrapper) {
                                    targetWrapper = document.getElementById('current-player-avatar-wrapper');
                                }
                                var avatar = targetWrapper ? targetWrapper.querySelector('.avatar-square') : null;
                                if (avatar) {
                                    if (ptsNum < 0) {
                                        // === ANIMATION PERTE DE POINTS ===
                                        avatar.classList.add('avatar-penalized');
                                        if (window.SoundManager) SoundManager.play('malusImpact');
                                        // Popup points perdus
                                        var popup = document.createElement('div');
                                        popup.className = 'points-popup-penalty';
                                        popup.textContent = ptsNum + ' pts';
                                        targetWrapper.appendChild(popup);
                                        setTimeout(function() { popup.remove(); }, 4000);
                                        // Flammes
                                        var flameEmojis = ['\\ud83d\\udd25', '\\ud83d\\udca5', '\\u2620\\ufe0f', '\\ud83d\\udd25', '\\ud83d\\udc80', '\\ud83d\\udd25', '\\u26a1', '\\ud83d\\udd25'];
                                        for (var fi = 0; fi < 8; fi++) {
                                            var fl = document.createElement('div');
                                            fl.className = 'malus-flame';
                                            fl.textContent = flameEmojis[Math.floor(Math.random() * flameEmojis.length)];
                                            fl.style.left = (50 + (Math.random() - 0.5) * 120) + '%';
                                            fl.style.top = (50 + (Math.random() - 0.5) * 80) + '%';
                                            fl.style.animationDelay = (Math.random() * 0.6) + 's';
                                            fl.style.fontSize = (22 + Math.random() * 14) + 'px';
                                            targetWrapper.appendChild(fl);
                                            (function(el) { setTimeout(function() { el.remove(); }, 2500); })(fl);
                                        }
                                        setTimeout(function() { avatar.classList.remove('avatar-penalized'); }, 5000);
                                    } else {
                                        // === ANIMATION GAIN DE POINTS ===
                                        avatar.style.animation = 'winnerPulse 0.6s ease-in-out';
                                        createWinnerEffects(avatar);
                                        if (window.SoundManager) SoundManager.play('gainPoints');
                                    }
                                }
                            }, 300);
                        }
                    })();"""

content = content[:match_a.start()] + handler_a_new + content[match_a.end():]

# === 2) Remove createMalusEffects function (it's no longer needed) ===
cm_pattern = r'\n                    // .* Effet malus .* flammes.*\n                    function createMalusEffects\(element\) \{.*?\n                    \}'
match_cm = re.search(cm_pattern, content, re.DOTALL)
if match_cm:
    print(f"Removing createMalusEffects at {match_cm.start()}-{match_cm.end()}")
    content = content[:match_cm.start()] + content[match_cm.end():]
else:
    print("WARNING: createMalusEffects not found (may already be removed)")

# === 3) Restore Handler B malus branch to original ===
# Replace the "// Malus gere par Handler A -- ne rien faire ici" with original malus code
hb_malus_old = """                                    if (pointsGained < 0) {
                                        // Malus g\u00e9r\u00e9 par Handler A \u2014 ne rien faire ici
                                    } else {"""

hb_malus_new = """                                    if (pointsGained < 0) {
                                        // === ANIMATION PERTE DE POINTS (FLAMMES + ETINCELLES) ===
                                        avatarSquare.classList.add('avatar-penalized');
                                        if (window.SoundManager) SoundManager.play('malusImpact');
                                        
                                        // Popup points perdus
                                        const popup = document.createElement('div');
                                        popup.className = 'points-popup-penalty';
                                        popup.textContent = pointsGained + ' pts';
                                        avatarWrapper.appendChild(popup);
                                        setTimeout(() => popup.remove(), 4000);
                                        
                                        // Flammes qui s'envolent autour de l'avatar
                                        const flames = ['\\ud83d\\udd25', '\\ud83d\\udca5', '\\u2620\\ufe0f', '\\ud83d\\udd25', '\\ud83d\\udc80', '\\ud83d\\udd25', '\\u26a1', '\\ud83d\\udd25'];
                                        for (let i = 0; i < 10; i++) {
                                            const flame = document.createElement('div');
                                            flame.className = 'malus-flame';
                                            flame.textContent = flames[Math.floor(Math.random() * flames.length)];
                                            flame.style.left = (50 + (Math.random() - 0.5) * 120) + '%';
                                            flame.style.top = (50 + (Math.random() - 0.5) * 80) + '%';
                                            flame.style.animationDelay = (Math.random() * 0.6) + 's';
                                            flame.style.fontSize = (22 + Math.random() * 14) + 'px';
                                            avatarWrapper.appendChild(flame);
                                            setTimeout(() => flame.remove(), 2500);
                                        }
                                        
                                        // Etincelles rouges/oranges
                                        const sparkColors = ['#DC3C3C', '#FF6B35', '#FF4500', '#8B0000', '#FF8C00'];
                                        for (let i = 0; i < 12; i++) {
                                            const spark = document.createElement('div');
                                            spark.className = 'malus-spark';
                                            spark.style.background = sparkColors[Math.floor(Math.random() * sparkColors.length)];
                                            spark.style.left = '50%';
                                            spark.style.top = '50%';
                                            const angle = (Math.PI * 2 * i) / 12;
                                            const dist = 40 + Math.random() * 40;
                                            spark.style.setProperty('--sx', Math.cos(angle) * dist + 'px');
                                            spark.style.setProperty('--sy', Math.sin(angle) * dist + 'px');
                                            spark.style.animationDelay = (Math.random() * 0.3) + 's';
                                            avatarWrapper.appendChild(spark);
                                            setTimeout(() => spark.remove(), 1800);
                                        }
                                        
                                        setTimeout(() => avatarSquare.classList.remove('avatar-penalized'), 5000);
                                    } else {"""

if hb_malus_old in content:
    content = content.replace(hb_malus_old, hb_malus_new)
    print("Restored Handler B malus branch")
else:
    print("WARNING: Handler B malus skip block not found")

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE - all changes applied")
