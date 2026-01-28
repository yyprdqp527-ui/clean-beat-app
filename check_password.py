import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Vérifier le compte maryline
c.execute("SELECT email, name, password, house_id FROM users WHERE email='maryline@hotmail.com'")
user = c.fetchone()

if user:
    email, name, password, house_id = user
    print(f'📧 Compte trouvé:')
    print(f'  Email: {email}')
    print(f'  Nom: {name}')
    print(f'  Maison: {house_id}')
    print(f'  Mot de passe hashé: {"OUI" if password and len(password) > 10 else "NON ou INVALIDE"}')
    if password:
        print(f'  Longueur hash: {len(password)} caractères')
        print(f'  Début hash: {password[:20]}...')
else:
    print('❌ Compte non trouvé')

conn.close()
