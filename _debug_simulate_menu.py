#!/usr/bin/env python3
"""Simuler exactement ce que /menu renvoie pour un user avec des messages non lus"""
import sqlite3

DB = 'users.db'

def get_unread_message_count(user_email, house_id, conn=None):
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM messages m
        WHERE m.house_id = ?
        AND m.recipient_email = ?
        AND m.message_type = 'private'
        AND NOT EXISTS (
            SELECT 1 FROM message_reads mr 
            WHERE mr.message_id = m.id 
            AND mr.user_email = ?
        )
    """, (house_id, user_email, user_email))
    return c.fetchone()[0]

def get_unread_baby_events_count(user_email, house_id, conn=None):
    c = conn.cursor()
    c.execute("""
        SELECT last_view_timestamp FROM baby_events_views
        WHERE user_email = ? AND house_id = ?
    """, (user_email, house_id))
    row = c.fetchone()
    if row and row[0]:
        c.execute("""
            SELECT COUNT(*) FROM baby_tracking bt
            WHERE bt.house_id = ? AND bt.created_at > ? AND bt.user_email != ?
        """, (house_id, row[0], user_email))
    else:
        c.execute("""
            SELECT COUNT(*) FROM baby_tracking bt
            WHERE bt.house_id = ? AND bt.user_email != ?
        """, (house_id, user_email))
    return c.fetchone()[0]

conn = sqlite3.connect(DB)
c = conn.cursor()

# Test for each user in house 149 (baconjean@hotmail.com has 4 unread)
c.execute("SELECT email, house_id, name FROM users WHERE house_id = 149")
users = c.fetchall()

print("=== SIMULATION /menu pour chaque user de house 149 ===")
for email, house_id, name in users:
    unread_messages_count = get_unread_message_count(email, house_id, conn)
    unread_baby_tracking = get_unread_baby_events_count(email, house_id, conn)
    
    courses_pending_count = 0
    c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (house_id,))
    courses_pending_count = c.fetchone()[0] or 0
    
    rooms_with_new_missions = {}
    c.execute("""
        SELECT ct.category, COUNT(*) as pending_count 
        FROM custom_tasks ct
        WHERE ct.house_id = ?
        AND NOT EXISTS (
            SELECT 1 FROM completed_tasks ctd
            WHERE ctd.house_id = ct.house_id
            AND (
                (ctd.related_task_id IS NOT NULL AND ctd.related_task_id = ct.id)
                OR (ctd.related_task_id IS NULL AND ctd.task_name = ct.task_name AND ctd.category = ct.category)
            )
        )
        GROUP BY ct.category
    """, (house_id,))
    rooms_with_new_missions = {row[0]: row[1] for row in c.fetchall()}
    
    print(f"\n--- User: {name} ({email}) ---")
    print(f"  unread_messages_count = {unread_messages_count}")
    print(f"  unread_baby_tracking  = {unread_baby_tracking}")
    print(f"  courses_pending_count = {courses_pending_count}")
    print(f"  rooms_with_new_missions = {rooms_with_new_missions}")
    
    # Ce que Jinja afficherait pour le badge
    badge_visible = "VISIBLE" if unread_messages_count > 0 else "HIDDEN (display:none)"
    badge_text = unread_messages_count if unread_messages_count and unread_messages_count < 100 else '99+'
    print(f"  Badge Jinja SSR: {badge_visible}, texte='{badge_text}'")
    
    # Ce que le bandeau debug V4 montrerait
    dbg_miss_len = len(rooms_with_new_missions)
    print(f"  Debug V4: SSR: MSG={unread_messages_count} BABY={unread_baby_tracking} CRS={courses_pending_count} MISS={dbg_miss_len}")

conn.close()
