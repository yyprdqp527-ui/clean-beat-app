import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Chercher les emails contenant maryline
c.execute("SELECT email, name, house_id FROM users WHERE LOWER(email) LIKE '%maryline%' ORDER BY email")
users = c.fetchall()

if users:
    print('📧 Utilisateurs trouvés avec "maryline":')
    for email, name, house_id in users:
        print(f'  • {email} - {name} (Maison {house_id})')
else:
    print('❌ Aucun utilisateur trouvé avec "maryline"')
    print()
    print('Recherche avec "mary":')
    c.execute("SELECT email, name, house_id FROM users WHERE LOWER(email) LIKE '%mary%' OR LOWER(name) LIKE '%mary%' ORDER BY email")
    mary_users = c.fetchall()
    if mary_users:
        print('📧 Utilisateurs trouvés avec "mary":')
        for email, name, house_id in mary_users:
            print(f'  • {email} - {name} (Maison {house_id})')
    else:
        print('❌ Aucun utilisateur trouvé avec "mary"')

conn.close()
