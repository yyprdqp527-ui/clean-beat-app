#!/usr/bin/env python3
import sqlite3
from datetime import datetime

DB = 'users.db'

def test_send_message():
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        house_id = 154
        sender_email = 'child_154_1770283322@cleanbeat.internal'
        content = '👶 Marinette TEST - a changé les couches à 10:35\n📝 Super sales'
        message_type = 'baby_tracking'
        
        print(f'🧪 Test création message baby_tracking:')
        print(f'   house_id: {house_id}')
        print(f'   sender_email: {sender_email}')
        print(f'   content: {content}')
        
        # Test insertion directe
        c.execute("""
            INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, timestamp)
            VALUES (?, ?, 'house', ?, ?, ?)
        """, (house_id, sender_email, content, message_type, datetime.now().isoformat()))
        
        message_id = c.lastrowid
        conn.commit()
        
        print(f'✅ Message créé avec ID: {message_id}')
        
        # Vérifier qu'il est récupéré par la requête /comments
        c.execute('''
            SELECT m.id, m.content, sender.name
            FROM messages m
            LEFT JOIN users sender ON m.sender_email = sender.email
            WHERE m.house_id = ? 
            AND (
                (m.message_type = 'private' AND (m.sender_email = 'ag@me.com' OR m.recipient_email = 'ag@me.com'))
                OR (m.sender_type = 'house' AND m.message_type NOT IN ('task_completed'))
            )
            AND m.id = ?
        ''', (house_id, message_id))
        
        result = c.fetchone()
        if result:
            print(f'✅ Message récupérable par /comments: ID {result[0]}, {result[2]}')
        else:
            print(f'❌ Message non récupérable par /comments')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ Erreur: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_send_message()