#!/usr/bin/env python3
"""Test: simuler le rendu des badges exactement comme /menu"""
import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()
user_email = 'agdaval@yahoo.fr'
house_id = 149

# 1. unread_messages_count
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
unread_messages_count = c.fetchone()[0]

# 2. courses_pending_count
c.execute("SELECT COUNT(*) FROM player_reminders WHERE house_id=? AND is_done=0", (house_id,))
courses_pending_count = c.fetchone()[0] or 0

# 3. rooms_with_new_missions
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

conn.close()

print("=== SIMULER /menu pour agdaval@yahoo.fr ===")
print(f"unread_messages_count = {unread_messages_count}")
print(f"courses_pending_count = {courses_pending_count}")
print(f"rooms_with_new_missions = {rooms_with_new_missions}")
print()

# Simuler Jinja2 pour le badge message
if not unread_messages_count or unread_messages_count <= 0:
    badge_style = "display:none;"
else:
    badge_style = ""
badge_text = unread_messages_count if unread_messages_count and unread_messages_count < 100 else "99+"

print(f"Badge MSG: style='{badge_style}' text='{badge_text}'")
print(f"Badge MSG VISIBLE? {badge_style == ''}")

# Simuler pour courses
if not courses_pending_count or courses_pending_count <= 0:
    crs_style = "display:none;"
else:
    crs_style = ""

print(f"Badge CRS: style='{crs_style}'")
print(f"Badge CRS VISIBLE? {crs_style == ''}")
print(f"Mission dots: {rooms_with_new_missions}")

# Debug banner output
print(f"\nSSR DEBUG: MSG={unread_messages_count} BABY=? CRS={courses_pending_count} MISS={len(rooms_with_new_missions)}")
