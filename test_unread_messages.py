import sqlite3

DB = 'users.db'
user_email = 'ag@me.com'
house_id = 154

conn = sqlite3.connect(DB)
c = conn.cursor()

# Messages REÇUS non lus
c.execute("""
    SELECT m.sender_email, COUNT(*) as unread_count
    FROM messages m
    WHERE m.house_id = ?
    AND m.message_type = 'private'
    AND m.recipient_email = ?
    AND m.id NOT IN (
        SELECT message_id FROM message_reads WHERE user_email = ?
    )
    AND m.sender_email IS NOT NULL
    AND m.sender_email != ?
    GROUP BY m.sender_email
""", (house_id, user_email, user_email, user_email))
received = dict(c.fetchall())
print('Messages REÇUS non lus:', received)

# Messages ENVOYÉS non lus
c.execute("""
    SELECT m.recipient_email, COUNT(*) as unread_count
    FROM messages m
    WHERE m.house_id = ?
    AND m.message_type = 'private'
    AND m.sender_email = ?
    AND m.id NOT IN (
        SELECT message_id FROM message_reads WHERE user_email = m.recipient_email
    )
    AND m.recipient_email IS NOT NULL
    AND m.recipient_email != ?
    GROUP BY m.recipient_email
""", (house_id, user_email, user_email))
sent = dict(c.fetchall())
print('Messages ENVOYÉS non lus:', sent)

# Total
all_players = set(received.keys()) | set(sent.keys())
result = {p: received.get(p, 0) + sent.get(p, 0) for p in all_players}
print('TOTAL par joueur:', result)

conn.close()
