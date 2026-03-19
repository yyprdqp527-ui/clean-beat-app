#!/usr/bin/env python3
"""
Script pour attribuer des couleurs vives et harmonieuses à tous les joueurs.
Fonctionne en local (SQLite) et en production (PostgreSQL sur Render).

Usage local  : python3 assign_player_colors.py
Usage Render : DATABASE_URL=postgresql://... python3 assign_player_colors.py
               (ou via la console Render avec DATABASE_URL déjà dans l'env)
"""

import os
import sqlite3

DB = 'users.db'

# ─── Palette : couleurs vives, bien contrastées, harmonieuses ───────────────
PLAYER_COLOR_PALETTE = [
    '#FF4D6D',  # 1  Rouge framboise
    '#00B4D8',  # 2  Bleu azur
    '#06D6A0',  # 3  Vert menthe vif
    '#FFB703',  # 4  Jaune soleil
    '#8B5CF6',  # 5  Violet électrique
    '#F77F00',  # 6  Orange vif
    '#3A86FF',  # 7  Bleu roi
    '#FF006E',  # 8  Rose choc
    '#2DC653',  # 9  Vert lime
    '#FB5607',  # 10 Orange brûlé
    '#9B5DE5',  # 11 Violet lilas
    '#00F5D4',  # 12 Turquoise néon
]

# ─── Connexion DB (SQLite local ou PostgreSQL selon DATABASE_URL) ────────────
_PG_URL = os.environ.get('DATABASE_URL', '')
if _PG_URL.startswith('postgres://'):
    _PG_URL = _PG_URL.replace('postgres://', 'postgresql://', 1)
_USE_PG = bool(_PG_URL)

def get_conn():
    if _USE_PG:
        import psycopg2
        conn = psycopg2.connect(_PG_URL, connect_timeout=10)
        conn.autocommit = False
        return conn, True
    else:
        conn = sqlite3.connect(DB)
        return conn, False

def placeholder(is_pg):
    return '%s' if is_pg else '?'

# ─── Main ────────────────────────────────────────────────────────────────────
print('=' * 70)
print('🎨  ATTRIBUTION DES COULEURS AUX JOUEURS')
print(f'    Base : {"PostgreSQL" if _USE_PG else "SQLite local"}')
print('=' * 70)

conn, is_pg = get_conn()
c = conn.cursor()
ph = placeholder(is_pg)

# S'assurer que la colonne existe
try:
    c.execute("SELECT player_color FROM users LIMIT 1")
    print('\n✅ Colonne player_color présente')
except Exception:
    conn.rollback()
    print('\n⚠️  Colonne player_color absente — ajout...')
    c.execute("ALTER TABLE users ADD COLUMN player_color TEXT")
    conn.commit()
    print('✅ Colonne ajoutée')

# Récupérer toutes les maisons
c.execute("SELECT id, name, house_name FROM houses")
houses = c.fetchall()
print(f'\n📊 {len(houses)} maison(s) trouvée(s)')
print('-' * 70)

total_updated = 0

for house_row in houses:
    house_id, h_name, h_house_name = house_row
    house_display = h_house_name or h_name or f'Maison #{house_id}'

    c.execute(f"""
        SELECT email, name, player_color
        FROM users
        WHERE house_id = {ph}
        ORDER BY email
    """, (house_id,))
    players = c.fetchall()

    if not players:
        continue

    print(f'\n🏠  {house_display}  ({len(players)} joueur(s))')

    used_colors = [row[2] for row in players if row[2]]
    players_to_update = []

    for email, player_name, current_color in players:
        display = player_name or email.split('@')[0]

        if current_color:
            print(f'   ✓  {display:<20} {current_color}  (déjà définie)')
        else:
            # Choisir la première couleur de la palette pas encore utilisée
            available = [col for col in PLAYER_COLOR_PALETTE if col not in used_colors]
            if not available:
                available = PLAYER_COLOR_PALETTE  # cycle si > 12 joueurs
            color = available[0]
            used_colors.append(color)
            players_to_update.append((color, email))
            print(f'   🎨  {display:<20} {color}  ← nouvelle')

    if players_to_update:
        for color, email in players_to_update:
            c.execute(
                f"UPDATE users SET player_color = {ph} WHERE email = {ph}",
                (color, email)
            )
            total_updated += 1

conn.commit()
conn.close()

print('\n' + '=' * 70)
print(f'✅  TERMINÉ : {total_updated} joueur(s) mis à jour')
print('=' * 70)
print('\n🎨  Palette utilisée :')
names = [
    'Rouge framboise', 'Bleu azur', 'Vert menthe vif', 'Jaune soleil',
    'Violet électrique', 'Orange vif', 'Bleu roi', 'Rose choc',
    'Vert lime', 'Orange brûlé', 'Violet lilas', 'Turquoise néon',
]
for i, (col, name) in enumerate(zip(PLAYER_COLOR_PALETTE, names), 1):
    print(f'   {i:2d}.  {col}  —  {name}')
