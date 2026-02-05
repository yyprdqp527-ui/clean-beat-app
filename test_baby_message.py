#!/usr/bin/env python3
"""Test d'insertion d'un message baby_tracking"""
import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Simuler un message baby_tracking correctement formé
house_id = 154
player_email = 'ag@me.com'
player_name = 'Anne-Gaelle'

# Obtenir le nom du joueur
c.execute('SELECT name FROM users WHERE email=?', (player_email,))
row = c.fetchone()
if row and row[0]:
    player_name = row[0]

tracking_time = '09:15'
bottle_ml = '150'
observations = 'Bebe a bien mange'

message_text = f'🍼 {player_name} a donne le biberon a {tracking_time} ({bottle_ml} ml)\n📝 {observations}'

# Insérer le message avec sender_email = player_email
c.execute('''
    INSERT INTO messages (house_id, sender_email, sender_type, content, message_type)
    VALUES (?, ?, 'house', ?, 'baby_tracking')
''', (house_id, player_email, message_text))

conn.commit()
print(f'✅ Message baby_tracking insere avec sender_email = {player_email}')

# Vérifier
c.execute('SELECT id, sender_email, content FROM messages WHERE message_type="baby_tracking" ORDER BY id DESC LIMIT 3')
for row in c.fetchall():
    print(f'ID={row[0]}, sender={row[1]}: {row[2][:50]}...')

conn.close()
