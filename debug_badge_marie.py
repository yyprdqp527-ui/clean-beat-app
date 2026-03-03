import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

marie = 'marie@me.com'
house_id = 158

print('=== BADGE MENU (ancienne logique) ===')
c.execute('''SELECT COUNT(*) FROM messages m
    WHERE m.house_id = ?
    AND m.id NOT IN (SELECT message_id FROM message_reads WHERE user_email = ?)
    AND (m.sender_email IS NULL OR m.sender_email != ?)
    AND m.message_type != 'task_completed'
''', (house_id, marie, marie))
print(f'Badge ANCIEN pour Marie: {c.fetchone()[0]}')

print()
print('=== BADGE MENU (nouvelle logique apres fix) ===')
c.execute('''SELECT COUNT(*) FROM messages m
    WHERE m.house_id = ?
    AND m.id NOT IN (SELECT message_id FROM message_reads WHERE user_email = ?)
    AND (m.sender_email IS NULL OR m.sender_email != ?)
    AND m.message_type NOT IN ('task_completed')
    AND (
        (m.message_type = 'private' AND (m.sender_email = ? OR m.recipient_email = ?))
        OR (m.sender_type = 'house')
    )
''', (house_id, marie, marie, marie, marie))
print(f'Badge NOUVEAU pour Marie: {c.fetchone()[0]}')

print()
print('=== TOUS MESSAGES + ETAT LU PAR MARIE ===')
c.execute('''SELECT m.id, m.sender_email, m.sender_type, m.message_type, m.recipient_email,
    CASE WHEN mr.message_id IS NOT NULL THEN 'LU' ELSE 'NON-LU' END as status
    FROM messages m
    LEFT JOIN message_reads mr ON m.id = mr.message_id AND mr.user_email = ?
    WHERE m.house_id = ?
    ORDER BY m.id
''', (marie, house_id))
print('id | sender | sender_type | msg_type | recipient | status')
for r in c.fetchall():
    print(f'  {r[0]} | {str(r[1])[:25]} | {r[2]} | {r[3]} | {str(r[4])[:30]} | {r[5]}')

print()
print('=== MESSAGE_READS DE MARIE ===')
c.execute('SELECT message_id, read_at FROM message_reads WHERE user_email = ? ORDER BY message_id', (marie,))
for r in c.fetchall():
    print(f'  msg_id={r[0]} | lu a: {r[1]}')

conn.close()
