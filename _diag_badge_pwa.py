#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()

c.execute("SELECT id, name FROM houses LIMIT 10")
print("=== Maisons ===")
for r in c.fetchall():
    print(r)

c.execute("""
    SELECT ct.house_id, ct.category, ct.task_name, ct.id
    FROM custom_tasks ct
    WHERE NOT EXISTS (
        SELECT 1 FROM completed_tasks ctd
        WHERE ctd.house_id = ct.house_id
        AND (
            (ctd.related_task_id IS NOT NULL AND ctd.related_task_id = ct.id)
            OR (ctd.related_task_id IS NULL AND ctd.task_name = ct.task_name AND ctd.category = ct.category)
        )
    )
    ORDER BY ct.house_id
    LIMIT 30
""")
print("\n=== custom_tasks non validees (source badge missions) ===")
for r in c.fetchall():
    print(r)

c.execute("SELECT house_id, COUNT(*) FROM player_reminders WHERE is_done=0 GROUP BY house_id")
print("\n=== Articles courses non coches par maison ===")
for r in c.fetchall():
    print(r)

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%baby%'")
print("\n=== Tables baby ===", [r[0] for r in c.fetchall()])

conn.close()
