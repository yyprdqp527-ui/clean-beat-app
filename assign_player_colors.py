#!/usr/bin/env python3
"""
Script pour attribuer des couleurs à tous les joueurs existants
"""

import sqlite3
import random

DB = 'users.db'

# Palette de couleurs harmonieuses
PLAYER_COLOR_PALETTE = [
    '#FF6B9D',  # Rose vif
    '#4ECDC4',  # Turquoise
    '#FFD93D',  # Jaune doré
    '#95E1D3',  # Menthe
    '#C7CEEA',  # Lavande
    '#FFA07A',  # Saumon
    '#98D8C8',  # Vert d'eau
    '#F7B7A3',  # Pêche
    '#A8DADC',  # Bleu ciel
    '#FFB6B9',  # Rose poudré
    '#B4A7D6',  # Violet pastel
    '#FFE66D',  # Jaune pastel
]

print('=' * 80)
print('🎨 ATTRIBUTION DES COULEURS AUX JOUEURS')
print('=' * 80)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Vérifier que la colonne player_color existe
try:
    c.execute("SELECT player_color FROM users LIMIT 1")
    print('\n✅ Colonne player_color existe')
except sqlite3.OperationalError:
    print('\n❌ Colonne player_color n\'existe pas - ajout en cours...')
    c.execute("ALTER TABLE users ADD COLUMN player_color TEXT")
    conn.commit()
    print('✅ Colonne player_color ajoutée')

# Récupérer toutes les maisons
c.execute("SELECT id, name, house_name FROM houses")
houses = c.fetchall()

print(f'\n📊 {len(houses)} maisons trouvées')
print('-' * 80)

total_players_updated = 0

for house_id, name, house_name in houses:
    house_display_name = house_name or name or f"Maison #{house_id}"
    
    # Récupérer les joueurs de cette maison
    c.execute("""
        SELECT email, name, player_color
        FROM users
        WHERE house_id = ?
        ORDER BY email
    """, (house_id,))
    
    players = c.fetchall()
    
    if not players:
        continue
    
    print(f'\n🏠 {house_display_name}')
    print(f'   {len(players)} joueur(s)')
    
    # Attribuer des couleurs aux joueurs qui n'en ont pas
    used_colors = []
    players_to_update = []
    
    for email, player_name, current_color in players:
        display_name = player_name or email.split('@')[0]
        
        if current_color:
            print(f'   ✓ {display_name}: {current_color} (déjà définie)')
            used_colors.append(current_color)
        else:
            # Trouver une couleur disponible
            available_colors = [c for c in PLAYER_COLOR_PALETTE if c not in used_colors]
            if not available_colors:
                # Si toutes les couleurs sont utilisées, recommencer
                available_colors = PLAYER_COLOR_PALETTE
            
            color = available_colors[0]
            used_colors.append(color)
            players_to_update.append((color, email))
            print(f'   🎨 {display_name}: {color} (nouvelle)')
    
    # Mettre à jour les couleurs dans la base de données
    if players_to_update:
        for color, email in players_to_update:
            c.execute("UPDATE users SET player_color = ? WHERE email = ?", (color, email))
            total_players_updated += 1

conn.commit()
conn.close()

print('\n' + '=' * 80)
print(f'✅ TERMINÉ : {total_players_updated} joueur(s) mis à jour avec des couleurs')
print('=' * 80)
print('\n💡 Les couleurs seront maintenant affichées dans toute l\'application :')
print('   • Avatars avec bordures colorées')
print('   • Barres de points personnalisées')
print('   • Messages et commentaires')
print('   • Cartes de joueurs')
print('\n🎨 Palette de couleurs utilisée :')
for i, color in enumerate(PLAYER_COLOR_PALETTE, 1):
    print(f'   {i:2d}. {color}')
