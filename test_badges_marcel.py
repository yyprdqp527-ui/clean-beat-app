import sqlite3
import sys
sys.path.insert(0, '/Users/anne-gaelledaval/Downloads/Appli web-2')
from app import get_house_players_points, get_unread_messages_by_sender

DB = 'users.db'
user_email = 'gfufgjdgdye@me.com'  # marcel
house_id = 150

print("=" * 60)
print(f"DEBUG pour {user_email} dans maison {house_id}")
print("=" * 60)

# Récupérer les joueurs
players = get_house_players_points(house_id)
print(f"\n📋 PLAYERS ({len(players)} joueurs):")
for i, p in enumerate(players):
    print(f"  [{i}] email='{p.get('email')}', name='{p.get('name')}'")

# Récupérer les messages non lus par sender
unread_by_sender = get_unread_messages_by_sender(user_email, house_id)
print(f"\n📬 UNREAD_BY_SENDER ({len(unread_by_sender)} entrées):")
for email, count in unread_by_sender.items():
    print(f"  '{email}': {count} messages")

# Vérifier les correspondances
print(f"\n🔍 CORRESPONDANCES:")
for p in players:
    p_email = p.get('email')
    if p_email == user_email:
        print(f"  ✓ {p.get('name')} ({p_email}) = joueur actuel (skip)")
        continue
    
    if p_email in unread_by_sender:
        print(f"  ✅ {p.get('name')} ({p_email}) -> BADGE: {unread_by_sender[p_email]}")
    else:
        print(f"  ❌ {p.get('name')} ({p_email}) -> PAS DE BADGE")

print("=" * 60)
