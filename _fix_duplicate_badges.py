#!/usr/bin/env python3
"""
Fix: Supprimer le bloc 2 dupliqué de refreshAllBadges/refreshMissionDots dans menu.html.

DIAGNOSTIC:
- Il y a DEUX définitions de refreshAllBadges() et refreshMissionDots() dans le même <script>.
- Le bloc 2 (simplifié, mauvais sélecteurs) ÉCRASE le bloc 1 (robuste) via le hoisting JS.
- Le bloc 2 cherche #room-baby-dot et .room-mission-dot qui n'existent pas dans le HTML Jinja.
- Le bloc 1 cherche .room-baby-badge et .room-new-mission-badge (corrects).
- Résultat : les pastilles ne s'affichent jamais au premier chargement.

FIX:
1. Supprimer les définitions dupliquées (refreshAllBadges, refreshMissionDots) du bloc 2
2. Supprimer les handlers dupliqués (pageshow, visibilitychange, DOMContentLoaded, SW listener)
3. Supprimer le pré-affichage Jinja dupliqué (l'IIFE du bloc 2)
4. Garder UNIQUEMENT les exports window.refreshAllBadges/refreshMissionDots
5. Ajouter ces exports juste après les définitions dans le bloc 1
"""

filepath = 'templates/menu.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
total = len(lines)
print(f"Total lignes: {total}")

# === ÉTAPE 1 : Ajouter les exports window. dans le bloc 1 ===
# Chercher la fin de la première IIFE de pré-affichage (bloc 1) pour insérer juste avant
# Le bloc 1 a un polling setInterval, juste après la IIFE
# On va insérer window.refreshAllBadges et window.refreshMissionDots 
# juste après la première déclaration de refreshAllBadges dans le bloc 1

# Trouver la ligne "// 🚀 Appel IMMÉDIAT" dans le bloc 1 (après l'IIFE)
insert_marker = None
for i, line in enumerate(lines):
    if '🚀 Appel IMMÉDIAT' in line and i < 5500:
        insert_marker = i
        break

if insert_marker:
    # Insérer les exports juste avant l'appel immédiat
    export_lines = [
        '                // Exposer globalement pour les handlers WebSocket et blocs script externes',
        '                window.refreshAllBadges = refreshAllBadges;',
        '                window.refreshMissionDots = refreshMissionDots;',
        ''
    ]
    for j, el in enumerate(export_lines):
        lines.insert(insert_marker + j, el)
    print(f"Étape 1: Exports window. insérés à la ligne {insert_marker + 1}")
    # Décaler les indices pour la suite
    offset = len(export_lines)
else:
    print("ERREUR: Marqueur '🚀 Appel IMMÉDIAT' non trouvé dans le bloc 1")
    offset = 0

# === ÉTAPE 2 : Supprimer le bloc 2 entier ===
# Chercher le début du bloc 2 : "// refreshAllBadges() — Recharge tous les badges depuis l'API"
# avec le séparateur ────
block2_start = None
block2_end = None

for i, line in enumerate(lines):
    if 'refreshAllBadges()' in line and 'Recharge tous les badges depuis l' in line and i > 5500:
        # Le séparateur ──── est 2 lignes avant
        block2_start = i - 2 if i >= 2 and '────' in lines[i-2] else i - 1
        break

if block2_start is None:
    print("ERREUR: Bloc 2 non trouvé")
else:
    # Trouver la fin : la balise </script> qui ferme ce bloc
    for i in range(block2_start, len(lines)):
        stripped = lines[i].strip()
        if stripped == '</script>':
            block2_end = i  # inclus
            break

    if block2_end is None:
        print("ERREUR: Fin du bloc 2 (</script>) non trouvée")
    else:
        # Supprimer les lignes du bloc 2, mais garder le </script>
        removed = block2_end - block2_start
        del lines[block2_start:block2_end]  # On garde la ligne </script>
        print(f"Étape 2: Bloc 2 supprimé (lignes {block2_start + 1} à {block2_end + 1}, {removed} lignes)")

# === ÉTAPE 3 : Écrire le résultat ===
new_content = '\n'.join(lines)
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

new_total = len(lines)
print(f"\nRésultat: {total} → {new_total} lignes (diff: {new_total - total})")
print("Done ✅")
