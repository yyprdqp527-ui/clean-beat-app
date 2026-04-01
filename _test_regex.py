import re
_RE_DATE_LOCALTIME = re.compile(r"DATE\(([^,)]+),\s*'localtime'\)", re.IGNORECASE)
_RE_DATE_COL = re.compile(r"\bdate\s*\(\s*([^'(),]+?)\s*\)", re.IGNORECASE)

sql = "DATE(COALESCE(ct.completed_at, ct.date_done)) = ?"
r1 = _RE_DATE_LOCALTIME.sub(r'\1::date', sql)
r2 = _RE_DATE_COL.sub(r'\1::date', r1)
print(f"Original:             {sql}")
print(f"After DATE_LOCALTIME: {r1}")
print(f"After DATE_COL:       {r2}")
print(f"Changed? {sql != r2}")

# Test avec CAST version
sql2 = "CAST(COALESCE(completed_at,date_done) AS TEXT) LIKE ?"
print(f"\nCAST version: {sql2}")
