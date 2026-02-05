#!/usr/bin/env python3
"""
Test pour créer manuellement un message baby_tracking pour Louisa
et vérifier l'affichage avec le bon avatar et nom
"""

import sqlite3
from datetime import datetime

def test_louisa_baby_message():
    """Test complet pour Louisa"""
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Info Louisa
    louisa_email = 'child_154_1770279933@cleanbeat.internal'
    house_id = 154
    
    # 1. Vérifier les données Louisa
    print("🔍 1. Vérification données Louisa:")
    c.execute("SELECT email, name, avatar, avatar_style, avatar_url FROM users WHERE email=?", (louisa_email,))
    louisa_data = c.fetchone()
    
    if louisa_data:
        email, name, avatar, avatar_style, avatar_url = louisa_data
        print(f"   📧 Email: {email}")
        print(f"   👤 Nom: {name}")
        print(f"   🎨 Avatar: {avatar}")
        print(f"   🎭 Style: {avatar_style}")
        print(f"   🌐 URL: {avatar_url}")
    else:
        print("   ❌ Louisa non trouvée!")
        return
    
    # 2. Créer un enregistrement baby_tracking
    print("\\n🍼 2. Création baby_tracking:")
    current_time = datetime.now().strftime('%H:%M')
    
    c.execute('''
        INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (louisa_email, house_id, 'biberon', current_time, 130, 'Test Louisa avec bon avatar'))
    
    tracking_id = c.lastrowid
    print(f"   ✅ Baby tracking créé: ID {tracking_id}")
    
    # 3. Créer le message baby_tracking
    print("\\n💬 3. Création message:")
    message_text = f'🍼 Louisa a donné le biberon à {current_time} (130 ml)\\n📝 Test Louisa avec bon avatar'
    
    c.execute('''
        INSERT INTO messages (house_id, sender_email, sender_type, content, message_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (house_id, louisa_email, 'house', message_text, 'baby_tracking', datetime.now().isoformat()))
    
    message_id = c.lastrowid
    print(f"   ✅ Message créé: ID {message_id}")
    print(f"   📝 Contenu: {message_text}")
    
    conn.commit()
    
    # 4. Test de la requête /comments avec jointure
    print("\\n🔍 4. Test requête /comments avec jointure:")
    c.execute("""
        SELECT m.id, m.sender_email, m.content, m.message_type,
               sender.name, sender.avatar, sender.avatar_style, sender.avatar_url
        FROM messages m
        LEFT JOIN users sender ON m.sender_email = sender.email
        WHERE m.house_id = ? AND m.id = ?
    """, (house_id, message_id))
    
    result = c.fetchone()
    if result:
        msg_id, sender_email, content, msg_type, sender_name, sender_avatar, sender_avatar_style, sender_avatar_url = result
        print(f"   ✅ Message trouvé dans /comments!")
        print(f"      📧 Sender: {sender_email}")
        print(f"      👤 Nom: {sender_name}")
        print(f"      🎨 Avatar: {sender_avatar}")
        print(f"      🎭 Style: {sender_avatar_style}")
        print(f"      🌐 URL: {sender_avatar_url}")
        print(f"      💬 Content: {content}")
        
        # Calculer l'URL finale qui sera affichée
        if sender_avatar_url:
            final_url = sender_avatar_url
            print(f"      🖼️ URL finale (depuis avatar_url): {final_url}")
        elif sender_avatar and len(str(sender_avatar)) <= 4:
            final_url = sender_avatar  # emoji
            print(f"      😀 Emoji: {final_url}")
        elif sender_avatar:
            style = sender_avatar_style if sender_avatar_style else 'adventurer'
            final_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={sender_avatar}"
            print(f"      🔗 URL reconstruite: {final_url}")
        else:
            final_url = "👤"
            print(f"      🚫 Fallback: {final_url}")
            
    else:
        print("   ❌ Message non trouvé!")
    
    conn.close()
    
    print("\\n✅ Test terminé!")
    print("🌐 Pour voir le résultat: http://192.168.1.149:8000/comments")
    print("📋 Connectez-vous avec ag@me.com / test")

if __name__ == "__main__":
    test_louisa_baby_message()