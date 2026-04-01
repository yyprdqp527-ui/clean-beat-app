#!/usr/bin/env python3
"""Diagnostic des compteurs de badges"""
import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Messages récents
c.execute("SELECT id, sender_email, recipient_email, message_type, timestamp FROM messages ORDER BY id DESC LIMIT 5")
print("=== Derniers messages ===")
for r in c.fetchall():
    print(f"  ID={r[0]} from={r[1]} to={r[2]} type={r[3]} at={r[4]}")

# Message reads
c.execute("PRAGMA table_info(message_reads)")
print("\n=== message_reads columns:", [r[1] for r in c.fetchall()])
c.execute("SELECT * FROM message_reads ORDER BY rowid DESC LIMIT 5")
for r in c.fetchall():
    print(f"  {r}")

# Compteurs par user
c.execute("SELECT DISTINCT email, house_id FROM users WHERE house_id IS NOT NULL LIMIT 10")
users = c.fetchall()
print("\n=== Compteurs par user ===")
for email, hid in users:
    c.execute("SELECT COUNT(*) FROM messages WHERE house_id=? AND recipient_email=? AND message_type='private' AND id NOT IN (SELECT message_id FROM message_reads WHERE user_email=?)", (hid, email, email))
    priv = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages WHERE house_id=? AND message_type='baby_tracking' AND id NOT IN (SELECT message_id FROM message_reads WHERE user_email=?)", (hid, email))
    baby = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages WHERE house_id=? AND message_type='task_added' AND id NOT IN (SELECT message_id FROM message_reads WHERE user_email=?)", (hid, email))
    task = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages WHERE house_id=? AND message_type='courses_added' AND id NOT IN (SELECT message_id FROM message_reads WHERE user_email=?)", (hid, email))
    courses = c.fetchone()[0]
    if priv or baby or task or courses:
        print(f"  {email} (house={hid}): private={priv}, baby={baby}, task_added={task}, courses={courses}")

# Push subs
c.execute("SELECT user_email, COUNT(*) FROM push_subscriptions GROUP BY user_email")
print("\n=== Push subscriptions ===")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} sub(s)")

# Custom tasks (missions)
c.execute("SELECT COUNT(*) FROM custom_tasks")
print(f"\n=== Custom tasks: {c.fetchone()[0]} ===")
c.execute("PRAGMA table_info(custom_tasks)")
print("Columns:", [r[1] for r in c.fetchall()])

conn.close()
