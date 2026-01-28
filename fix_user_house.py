import sqlite3
import random
import string

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Trouver le dernier utilisateur créé
c.execute("SELECT email, name, house_id FROM users WHERE registration_step='profile_created' ORDER BY id DESC LIMIT 1")
result = c.fetchone()

if result:
    email, name, house_id = result
    print(f'Dernier utilisateur: {name} ({email})')
    print(f'House ID actuel: {house_id}')
    
    if not house_id:
        print('⚠️ PAS DE MAISON - Création en cours...')
        # Créer une maison pour cet utilisateur
        house_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        c.execute("INSERT INTO houses (name, house_name, level, health, mood, code, progress, last_reset_date) VALUES (?, ?, 1, 0, 'happy', ?, 0, date('now'))", 
                  ('', '', house_code))
        new_house_id = c.lastrowid
        c.execute('UPDATE users SET house_id=? WHERE email=?', (new_house_id, email))
        conn.commit()
        print(f'✅ Maison créée! House ID: {new_house_id}, Code: {house_code}')
    else:
        print('✅ L\'utilisateur a déjà une maison')
else:
    print('❌ Aucun utilisateur trouvé')

conn.close()
