#!/usr/bin/env python3
"""Debug: vérifier les données badge dans la DB locale"""
import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables)

# Users
print('\n=== USERS ===')
c.execute('SELECT email, house_id, is_child_account FROM users LIMIT 10')
for r in c.fetchall():
    print(f'  {r[0]} house={r[1]} child={r[2]}')

# Unread messages
print('\n=== MESSAGES NON LUS ===')
c.execute("""SELECT m.recipient_email, COUNT(*) as cnt 
  FROM messages m 
  WHERE m.message_type='private' 
  AND NOT EXISTS (SELECT 1 FROM message_reads mr WHERE mr.message_id = m.id AND mr.user_email = m.recipient_email)
  GROUP BY m.recipient_email""")
for r in c.fetchall():
    print(f'  Unread for {r[0]}: {r[1]}')

# Pending missions
print('\n=== MISSIONS EN ATTENTE ===')
c.execute("""SELECT ct.house_id, COUNT(*) FROM custom_tasks ct
  WHERE NOT EXISTS (
    SELECT 1 FROM completed_tasks ctd 
    WHERE ctd.house_id = ct.house_id 
    AND (
      (ctd.related_task_id IS NOT NULL AND ctd.related_task_id = ct.id)
      OR (ctd.related_task_id IS NULL AND ctd.task_name = ct.task_name AND ctd.category = ct.category)
    )
  )
  GROUP BY ct.house_id""")
for r in c.fetchall():
    print(f'  Pending missions house {r[0]}: {r[1]}')

# Courses pending
print('\n=== COURSES EN ATTENTE ===')
c.execute('SELECT house_id, COUNT(*) FROM player_reminders WHERE is_done=0 GROUP BY house_id')
for r in c.fetchall():
    print(f'  Courses pending house {r[0]}: {r[1]}')

# Baby tracking
print('\n=== BABY TRACKING ===')
c.execute('SELECT house_id, COUNT(*) FROM baby_tracking GROUP BY house_id')
for r in c.fetchall():
    print(f'  Baby events house {r[0]}: {r[1]}')

conn.close()
