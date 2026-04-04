import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT email, password FROM users WHERE email='nnbn@lkj.com'")
row = c.fetchone()
print(f"email: {row[0]}")
print(f"password hash: {row[1][:80]}...")

# Check if it's hashed
pwd = row[1]
if pwd.startswith('$') or pwd.startswith('pbkdf2') or pwd.startswith('scrypt'):
    print("Password is HASHED")
else:
    print(f"Password appears to be PLAIN: '{pwd}'")

# Also try duddu@me.com
c.execute("SELECT email, password FROM users WHERE email='duddu@me.com'")
row2 = c.fetchone()
print(f"\nduddu@me.com password hash: {row2[1][:80]}...")

conn.close()
