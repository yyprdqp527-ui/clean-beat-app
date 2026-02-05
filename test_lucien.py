#!/usr/bin/env python3
"""Test recherche Lucien"""
import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Chercher Lucien
c.execute("SELECT email, name FROM users WHERE name LIKE '%ucien%' AND house_id = 154")
lucien = c.fetchone()
if lucien:
    print(f'👦 Lucien trouvé: {lucien[0]} -> {lucien[1]}')
    
    # Chercher ses tâches récentes
    c.execute("""
        SELECT ct.user_email, ct.task_name, ct.completed_at
        FROM completed_tasks ct
        WHERE ct.user_email = ? 
        AND ct.task_name LIKE '%biberon%'
        ORDER BY ct.completed_at DESC
        LIMIT 5
    """, (lucien[0],))
    
    print('🍼 Validations biberon de Lucien:')
    for row in c.fetchall():
        print(f'  {row[1]} - {row[2]}')
        
    # Chercher ses messages baby_tracking
    c.execute("""
        SELECT m.id, m.content, m.timestamp, m.message_type
        FROM messages m
        WHERE m.sender_email = ? 
        AND m.message_type = 'baby_tracking'
        ORDER BY m.timestamp DESC
        LIMIT 5
    """, (lucien[0],))
    
    print('💬 Messages baby_tracking de Lucien:')
    for row in c.fetchall():
        print(f'  {row[1][:50]}... ({row[2]})')
else:
    print('❌ Lucien non trouvé')

conn.close()