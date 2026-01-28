import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Vérifier l'utilisateur agdaval
c.execute("SELECT email, name, house_id, registration_step FROM users WHERE email='agdaval@yahoo.fr'")
user = c.fetchone()

if user:
    print(f"✅ Utilisateur trouvé:")
    print(f"   Email: {user[0]}")
    print(f"   Nom: {user[1]}")
    print(f"   House ID: {user[2]}")
    print(f"   Étape: {user[3]}")
    
    if user[2]:
        # Vérifier la maison
        c.execute("SELECT id, name, house_name FROM houses WHERE id=?", (user[2],))
        house = c.fetchone()
        if house:
            print(f"\n✅ Maison trouvée:")
            print(f"   ID: {house[0]}")
            print(f"   Name: {house[1]}")
            print(f"   House_name: {house[2]}")
        else:
            print(f"\n❌ Maison {user[2]} introuvable!")
    else:
        print("\n❌ Pas de house_id!")
else:
    print("❌ Utilisateur agdaval@yahoo.fr introuvable!")

conn.close()
