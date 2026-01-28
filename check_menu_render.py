import sqlite3

# Vérifier l'état complet de l'utilisateur et de la maison
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Récupérer l'info utilisateur
c.execute("SELECT email, name, house_id, registration_step FROM users WHERE email='agdaval@yahoo.fr'")
user = c.fetchone()
if not user:
    print("❌ Utilisateur introuvable")
    exit(1)

email, name, house_id, reg_step = user
print(f"✅ Utilisateur: {email}, Nom: {name}, house_id: {house_id}, Étape: {reg_step}")

if not house_id:
    print("❌ Pas de house_id")
    exit(1)

# Vérifier la maison
c.execute("SELECT id, name, house_name FROM houses WHERE id=?", (house_id,))
house = c.fetchone()
if not house:
    print(f"❌ Maison {house_id} introuvable")
    exit(1)

h_id, h_name, h_house_name = house
print(f"✅ Maison: ID={h_id}, name='{h_name}', house_name='{h_house_name}'")

# Vérifier la condition show_house_name_form (lignes 4966-4967 de app.py)
name_empty = not h_name or not h_name.strip()
house_name_empty = not h_house_name or not h_house_name.strip()
show_form = name_empty and house_name_empty

print(f"\n📊 Analyse de la condition show_house_name_form:")
print(f"   name='{h_name}' → vide: {name_empty}")
print(f"   house_name='{h_house_name}' → vide: {house_name_empty}")
print(f"   Résultat: show_house_name_form = {show_form}")

if show_form:
    print("\n❌ PROBLÈME: Le formulaire de nom de maison sera affiché!")
    print("   Solution: Remplir le champ 'name' ou 'house_name' de la maison")
else:
    print("\n✅ Le formulaire ne devrait PAS s'afficher, le menu devrait être visible")
    
# Vérifier les joueurs
c.execute("SELECT email, name, avatar FROM users WHERE house_id=?", (house_id,))
players = c.fetchall()
print(f"\n👥 Joueurs dans la maison ({len(players)}):")
for p in players:
    print(f"   - {p[1]} ({p[0]}), avatar: {p[2]}")

conn.close()
