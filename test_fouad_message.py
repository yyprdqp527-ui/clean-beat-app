import sqlite3

DB = 'users.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

house_id = 154
user_email = 'ag@me.com'

# Reproduire la requête de /comments avec les JOINs
c.execute('''
    SELECT m.id, m.sender_email, m.recipient_email, m.content, m.timestamp, m.sender_type, m.message_type,
           sender.name, sender.avatar, sender.avatar_file, sender.avatar_url
    FROM messages m
    LEFT JOIN users sender ON m.sender_email = sender.email
    WHERE m.house_id = ? 
    AND (
        (m.message_type = 'private' AND (m.sender_email = ? OR m.recipient_email = ?))
        OR (m.sender_type = 'house' AND m.message_type NOT IN ('task_completed'))
    )
    ORDER BY m.timestamp DESC
    LIMIT 10
''', (house_id, user_email, user_email))

rows = c.fetchall()
print(f'📬 Messages récupérés: {len(rows)}\n')

for row in rows:
    msg_id, sender_email, recipient_email, content, timestamp, sender_type, message_type, sender_name, sender_avatar, sender_avatar_file, sender_avatar_url = row
    print(f'ID {msg_id}: type={message_type}')
    print(f'  sender_email: {sender_email}')
    print(f'  sender_type: {sender_type}')
    print(f'  sender_name (JOIN): {sender_name}')
    print(f'  sender_avatar: {sender_avatar}')
    print(f'  Content: {content[:50]}...')
    print()

conn.close()
