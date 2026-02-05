#!/usr/bin/env python3
"""Script de diagnostic pour les messages baby_tracking"""

import sqlite3

DB = 'users.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# Vérifier le house_id de l'utilisateur courant
print('='*60)
print('🏠 VÉRIFICATION DES HOUSE_ID:')
print('='*60)
c.execute('''
    SELECT email, house_id, name 
    FROM users 
    WHERE email IN (
        SELECT DISTINCT sender_email 
        FROM messages 
        WHERE message_type='baby_tracking'
    )
''')
for row in c.fetchall():
    print(f'  User: {row[0]}, house_id={row[1]}, name={row[2]}')

# Vérifier les messages baby_tracking avec leur house_id
print()
print('='*60)
print('🍼 HOUSE_ID DES MESSAGES BABY_TRACKING:')
print('='*60)
c.execute('''
    SELECT m.id, m.house_id, m.sender_email, m.content, m.sender_type, m.message_type
    FROM messages m
    WHERE m.message_type = 'baby_tracking'
    ORDER BY m.timestamp DESC
    LIMIT 5
''')
for row in c.fetchall():
    print(f'ID={row[0]}, house_id={row[1]}, sender={row[2]}')
    print(f'  sender_type={row[4]}, message_type={row[5]}')

# Simuler la requête exacte de /comments
print()
print('='*60)
print('🔍 SIMULATION REQUÊTE /comments (house_id=154):')
print('='*60)
user_email = 'ag@me.com'
house_id = 154

c.execute('''
    SELECT m.id, m.sender_email, m.content, m.sender_type, m.message_type
    FROM messages m
    WHERE m.house_id = ? 
    AND (
        (m.message_type = 'private' AND (m.sender_email = ? OR m.recipient_email = ?))
        OR (m.sender_type = 'house' AND m.message_type NOT IN ('task_completed'))
    )
    ORDER BY m.timestamp DESC
    LIMIT 15
''', (house_id, user_email, user_email))

rows = c.fetchall()
print(f'Nombre de messages: {len(rows)}')
baby_count = 0
for row in rows:
    if row[4] == 'baby_tracking':
        baby_count += 1
        print(f'  ID={row[0]}: {row[4]} - {row[2][:50]}...')
print(f'Dont baby_tracking: {baby_count}')

# Tester spécifiquement les messages récents
print()
print('='*60)
print('🔍 TOUS LES MESSAGES RÉCENTS de la maison 154:')
print('='*60)
c.execute('''
    SELECT m.id, m.sender_type, m.message_type, m.content
    FROM messages m
    WHERE m.house_id = 154
    ORDER BY m.timestamp DESC
    LIMIT 20
''')
for row in c.fetchall():
    content_preview = row[3][:40] if row[3] else ''
    print(f'  ID={row[0]}: sender_type={row[1]}, msg_type={row[2]} - {content_preview}...')

conn.close()
