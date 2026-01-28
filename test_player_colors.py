#!/usr/bin/env python3
"""
Test pour vérifier que les couleurs sont bien récupérées
"""

import sqlite3
import sys
import os

# Ajouter le chemin pour importer depuis app.py
sys.path.insert(0, os.path.dirname(__file__))

DB = 'users.db'

print('=' * 80)
print('🎨 TEST DES COULEURS DES JOUEURS')
print('=' * 80)

# Test 1: Vérifier que les couleurs existent dans la base
print('\n1️⃣ Vérification de la base de données:')
conn = sqlite3.connect(DB)
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM users WHERE player_color IS NOT NULL")
count = c.fetchone()[0]
print(f'   ✅ {count} joueurs ont une couleur définie')

# Test 2: Récupérer les joueurs d'une maison avec couleurs
print('\n2️⃣ Test de récupération des couleurs:')
c.execute("""
    SELECT house_id, COUNT(*) as nb
    FROM users
    WHERE house_id IS NOT NULL
    GROUP BY house_id
    HAVING nb > 1
    LIMIT 1
""")
result = c.fetchone()

if result:
    house_id = result[0]
    print(f'   🏠 Maison testée: ID={house_id}')
    
    c.execute("""
        SELECT email, name, player_color
        FROM users
        WHERE house_id = ?
        ORDER BY email
    """, (house_id,))
    
    players = c.fetchall()
    print(f'\n   Joueurs trouvés:')
    for email, name, color in players:
        display_name = name or email.split('@')[0]
        color_display = color if color else '❌ PAS DE COULEUR'
        print(f'   • {display_name}: {color_display}')

# Test 3: Tester la fonction get_house_players_points
print('\n3️⃣ Test de la fonction get_house_players_points():')
try:
    from app import get_house_players_points
    
    if result:
        players_data = get_house_players_points(house_id)
        print(f'   Fonction retourne {len(players_data)} joueur(s):')
        for p in players_data:
            name = p.get('name', 'Unknown')
            color = p.get('color', 'N/A')
            print(f'   • {name}: color={color}')
            
            if not color or color == 'N/A':
                print(f'   ⚠️  PROBLÈME: {name} n\'a pas de couleur!')
    else:
        print('   ⚠️ Aucune maison avec plusieurs joueurs trouvée')
        
except Exception as e:
    print(f'   ❌ ERREUR: {e}')
    import traceback
    traceback.print_exc()

conn.close()

print('\n' + '=' * 80)
print('FIN DU TEST')
print('=' * 80)
