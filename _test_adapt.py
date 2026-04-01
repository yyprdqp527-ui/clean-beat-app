#!/usr/bin/env python3
"""Test de la conversion _adapt() pour PostgreSQL"""
import re

_RE_STRFTIME_W = re.compile(r"strftime\s*\(\s*'%w'\s*,\s*(.+?)\s*\)", re.IGNORECASE)
_RE_DATETIME_DATE_NOW_OFFSET = re.compile(r"datetime\s*\(\s*date\s*\(\s*'now'\s*,\s*'localtime'\s*,\s*'([^']+)'\s*\)\s*\)", re.IGNORECASE)
_RE_DATETIME_DATE_NOW_LOCAL = re.compile(r"datetime\s*\(\s*date\s*\(\s*'now'\s*,\s*'localtime'\s*\)\s*\)", re.IGNORECASE)
_RE_DATETIME_COL = re.compile(r"datetime\s*\(\s*([^()]+?)\s*\)", re.IGNORECASE)
_RE_DATE_NOW_OFFSET = re.compile(r"date\s*\(\s*'now'\s*,\s*'localtime'\s*,\s*'([^']+)'\s*\)", re.IGNORECASE)
_RE_DATE_NOW_LOCAL = re.compile(r"date\s*\(\s*'now'\s*,\s*'localtime'\s*\)", re.IGNORECASE)
_RE_DATE_NOW = re.compile(r"date\s*\(\s*'now'\s*\)", re.IGNORECASE)
_RE_DATE_LOCALTIME = re.compile(r"DATE\(([^,)]+),\s*'localtime'\)", re.IGNORECASE)
_RE_DATE_COL = re.compile(r"\bdate\s*\(\s*([^'(),]+?)\s*\)", re.IGNORECASE)

def adapt(sql):
    sql = sql.replace('?', '%s')
    sql = _RE_STRFTIME_W.sub(r"EXTRACT(DOW FROM \1::date)::integer", sql)
    sql = _RE_DATETIME_DATE_NOW_OFFSET.sub(r"(CURRENT_DATE + INTERVAL '\1')::timestamp", sql)
    sql = _RE_DATETIME_DATE_NOW_LOCAL.sub('CURRENT_TIMESTAMP', sql)
    sql = _RE_DATETIME_COL.sub(r'\1::timestamp', sql)
    sql = _RE_DATE_NOW_OFFSET.sub(r"CURRENT_DATE + INTERVAL '\1'", sql)
    sql = _RE_DATE_NOW_LOCAL.sub('CURRENT_DATE', sql)
    sql = _RE_DATE_NOW.sub('CURRENT_DATE', sql)
    sql = _RE_DATE_LOCALTIME.sub(r'\1::date', sql)
    sql = _RE_DATE_COL.sub(r'\1::date', sql)
    return sql

# Test des requêtes critiques trouvées dans app.py
tests = [
    # validate_task doublon check
    "SELECT COUNT(*) FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at)=?",
    "SELECT id FROM completed_tasks WHERE user_email=? AND category=? AND task_name=? AND DATE(completed_at)=?",
    # WebSocket daily points
    "AND DATE(ct.completed_at) = DATE('now')",
    # DATE('now', '-30 days') 
    "WHERE DATE(completed_at) >= DATE('now','-30 days')",
    # Simple
    "DATE(completed_at)=?",
    "DATE(ct.completed_at) >= ?",
    # CAST patterns (should pass through)
    "CAST(completed_at AS TEXT) LIKE ?",
    "CAST(completed_at AS TEXT) >= ?",
]

print("=" * 80)
for t in tests:
    result = adapt(t)
    ok = "DATE(" not in result or "CURRENT_DATE" in result
    status = "✅" if ok else "❌"
    print(f"{status} IN:  {t}")
    print(f"   OUT: {result}")
    print()
