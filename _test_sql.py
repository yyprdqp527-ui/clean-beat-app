#!/usr/bin/env python3
"""Test SQL translation for PostgreSQL"""
import re

_RE_DATE_LOCALTIME = re.compile(r"DATE\(([^,)]+),\s*'localtime'\)", re.IGNORECASE)
_RE_DATE_NOW_LOCAL = re.compile(r"date\s*\(\s*'now'\s*,\s*'localtime'\s*\)", re.IGNORECASE)
_RE_DATE_NOW_OFFSET = re.compile(r"date\s*\(\s*'now'\s*,\s*'localtime'\s*,\s*'([^']+)'\s*\)", re.IGNORECASE)
_RE_DATE_NOW = re.compile(r"date\s*\(\s*'now'\s*\)", re.IGNORECASE)
_RE_DATE_COL = re.compile(r"\bdate\s*\(\s*([^'(),]+?)\s*\)", re.IGNORECASE)

queries = {
    "Doublon check": "SELECT id FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at, 'localtime')=?",
    "IN query": "SELECT email, house_id, name FROM users WHERE email IN (?, ?)",
    "WebSocket":  """SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
           COALESCE(SUM(ct.points), 0) as daily_points
    FROM users u
    LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
        AND DATE(ct.completed_at, 'localtime') = DATE('now', 'localtime')
    WHERE u.house_id = ?
    GROUP BY u.email
    ORDER BY daily_points DESC, u.points DESC""",
    "Daily batch": """SELECT user_email, COALESCE(SUM(points),0), COUNT(*)
    FROM completed_tasks
    WHERE house_id=? AND DATE(completed_at, 'localtime')=?
    GROUP BY user_email""",
    "Streak 60d": "AND DATE(completed_at, 'localtime') >= DATE('now', 'localtime', '-60 days')",
    "INSERT task": "INSERT INTO completed_tasks (user_email, house_id, category, task_name, points, completed_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
}

def adapt(sql):
    sql = sql.replace('?', '%s')
    sql = _RE_DATE_NOW_OFFSET.sub(r"CURRENT_DATE + INTERVAL '\1'", sql)
    sql = _RE_DATE_NOW_LOCAL.sub('CURRENT_DATE', sql)
    sql = _RE_DATE_NOW.sub('CURRENT_DATE', sql)
    sql = _RE_DATE_LOCALTIME.sub(r'\1::date', sql)
    sql = _RE_DATE_COL.sub(r'\1::date', sql)
    return sql

for name, q in queries.items():
    print(f"=== {name} ===")
    print(f"  SQLite: {q[:120]}")
    pg = adapt(q)
    print(f"  PG:     {pg[:120]}")
    print()
