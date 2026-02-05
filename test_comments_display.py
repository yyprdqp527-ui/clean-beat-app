#!/usr/bin/env python3
"""
Test pour vérifier l'affichage des messages baby_tracking dans la messagerie
"""

import sqlite3

DB = 'users.db'
house_id = 154
user_email = 'ag@me.com'

print("="*80)
print("🔍 TEST AFFICHAGE MESSAGES BABY_TRACKING")
print("="*80)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Reproduire exactement la requête utilisée dans /comments
print(f"\n1️⃣ Test de la requête SQL de /comments")
print(f"   house_id={house_id}, user={user_email}")

c.execute("""
    SELECT m.id, m.sender_email, m.recipient_email, m.content, m.timestamp, m.sender_type, m.message_type,
           sender.name, sender.avatar, sender.avatar_file, sender.avatar_url, sender.avatar_style,
           recipient.name, recipient.avatar, recipient.avatar_file, recipient.avatar_url
    FROM messages m
    LEFT JOIN users sender ON m.sender_email = sender.email
    LEFT JOIN users recipient ON m.recipient_email = recipient.email
    WHERE m.house_id = ? 
    AND (
        (m.message_type = 'private' AND (m.sender_email = ? OR m.recipient_email = ?))
        OR (m.sender_type = 'house' AND m.message_type NOT IN ('task_completed'))
    )
    ORDER BY m.timestamp DESC
    LIMIT 10
""", (house_id, user_email, user_email))

rows = c.fetchall()
print(f"\n✅ Nombre de messages récupérés: {len(rows)}")

baby_tracking_count = 0
for row in rows:
    msg_id, sender_email, recipient_email, content, timestamp, sender_type, message_type, sender_name, sender_avatar, sender_avatar_file, sender_avatar_url, sender_avatar_style, recipient_name, recipient_avatar, recipient_avatar_file, recipient_avatar_url = row
    
    if message_type == 'baby_tracking':
        baby_tracking_count += 1
        print(f"\n🍼 Message #{msg_id} (baby_tracking):")
        print(f"   sender_email: {sender_email}")
        print(f"   sender_name: {sender_name}")
        print(f"   sender_type: {sender_type}")
        print(f"   sender_avatar: {sender_avatar}")
        print(f"   sender_avatar_file: {sender_avatar_file}")
        print(f"   sender_avatar_url: {sender_avatar_url}")
        print(f"   sender_avatar_style: {sender_avatar_style}")
        print(f"   content: {content[:80]}...")
        print(f"   timestamp: {timestamp}")

print(f"\n📊 Résumé:")
print(f"   Total messages: {len(rows)}")
print(f"   Messages baby_tracking: {baby_tracking_count}")

if baby_tracking_count == 0:
    print("\n⚠️  PROBLÈME: Aucun message baby_tracking trouvé!")
    print("   Vérification des messages baby_tracking dans la base...")
    
    c.execute("SELECT COUNT(*) FROM messages WHERE house_id=? AND message_type='baby_tracking'", (house_id,))
    total_baby = c.fetchone()[0]
    print(f"   Total messages baby_tracking dans la base: {total_baby}")
else:
    print(f"\n✅ {baby_tracking_count} messages baby_tracking trouvés - tout fonctionne!")

conn.close()
print("\n" + "="*80)
