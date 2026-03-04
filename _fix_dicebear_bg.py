import sqlite3, re

conn = sqlite3.connect('/Users/anne-gaelledaval/Downloads/Appli web-2/users.db')
c = conn.cursor()

def fix_dicebear_url(url):
    if not url or 'dicebear.com' not in url:
        return url
    url = url.replace('/8.x/', '/7.x/')
    url = re.sub(r'[&?]backgroundColor=[^&]*', '', url).rstrip('?&')
    sep = '&' if '?' in url else '?'
    return url + sep + 'backgroundColor=transparent'

# Colonne avatar_url
c.execute("SELECT email, avatar_url FROM users WHERE avatar_url IS NOT NULL AND avatar_url LIKE '%dicebear.com%'")
rows = c.fetchall()
print("avatar_url DiceBear:", len(rows))
for email, av in rows:
    new = fix_dicebear_url(av)
    if new != av:
        c.execute("UPDATE users SET avatar_url=? WHERE email=?", (new, email))
        print(" AVANT:", av[:80])
        print(" APRES:", new[:80])

# Colonne avatar (si contient une URL DiceBear complete)
c.execute("SELECT email, avatar FROM users WHERE avatar IS NOT NULL AND avatar LIKE '%dicebear.com%'")
rows2 = c.fetchall()
print("avatar DiceBear:", len(rows2))
for email, av in rows2:
    new = fix_dicebear_url(av)
    if new != av:
        c.execute("UPDATE users SET avatar=? WHERE email=?", (new, email))
        print(" AVANT:", av[:80])
        print(" APRES:", new[:80])

conn.commit()
conn.close()
print("DONE")
