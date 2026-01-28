import sqlite3

DB = 'users.db'

# Test pour chaque utilisateur de la maison 149
conn = sqlite3.connect(DB)
c = conn.cursor()

users_149 = [
    'agdaval@yahoo.fr',
    'baconjean@hotmail.com',
    'maryline@hotmail.com',
    'child_149_1769510777@cleanbeat.internal',
    'child_149_1769531616@cleanbeat.internal'
]

for user_email in users_149:
    print(f"\n{'='*60}")
    print(f"Test pour: {user_email}")
    print(f"{'='*60}")
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id, name FROM users WHERE email=?", (user_email,))
    user_row = c.fetchone()
    
    if not user_row or not user_row[0]:
        print("❌ Pas de house_id pour cet utilisateur")
        continue
    
    house_id = user_row[0]
    current_user_name = user_row[1] if user_row[1] else user_email.split('@')[0]
    
    print(f"✓ House ID: {house_id}")
    print(f"✓ Nom: {current_user_name}")
    
    # Récupérer tous les joueurs de la maison (sauf l'utilisateur actuel)
    c.execute("""
        SELECT email, name, avatar, avatar_file, avatar_url
        FROM users 
        WHERE house_id = ? 
        AND email != ?
    """, (house_id, user_email))
    
    available_players = []
    for player_row in c.fetchall():
        player_email, player_name, player_avatar, player_avatar_file, player_avatar_url = player_row
        
        # Préparer l'avatar
        display_avatar = None
        if player_avatar_file:
            display_avatar = f"/static/uploads/{player_avatar_file}"
        elif player_avatar_url:
            display_avatar = player_avatar_url
        elif player_avatar and len(str(player_avatar)) <= 4:
            display_avatar = player_avatar
        else:
            display_avatar = '👤'
        
        available_players.append({
            'email': player_email,
            'name': player_name if player_name else player_email.split('@')[0],
            'avatar': display_avatar
        })
    
    print(f"\n✓ Partenaires disponibles: {len(available_players)}")
    for player in available_players:
        print(f"  - {player['name']} ({player['email']})")
        print(f"    Avatar: {player['avatar'][:50]}...")

conn.close()
