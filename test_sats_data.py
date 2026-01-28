"""Test pour vérifier les données renvoyées par la route /sats"""
import sqlite3
from datetime import date, timedelta

DB = 'users.db'

# Email de test
test_email = 'agdaval@yahoo.fr'

conn = sqlite3.connect(DB)
c = conn.cursor()

# Récupérer house_id
c.execute("SELECT house_id, name FROM users WHERE email=?", (test_email,))
row = c.fetchone()
if not row:
    print(f"❌ Utilisateur {test_email} introuvable")
    exit(1)

house_id, name = row
print(f"✅ Utilisateur: {name} ({test_email})")
print(f"🏠 House ID: {house_id}")
print()

# Récupérer tous les joueurs de la maison
c.execute("""
    SELECT email, name, points 
    FROM users WHERE house_id=?
""", (house_id,))
users_rows = c.fetchall()

print(f"👥 Joueurs dans la maison ({len(users_rows)}):")
print("-" * 60)

week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
today = date.today().isoformat()

print(f"📅 Aujourd'hui: {today}")
print(f"📅 Début de semaine (lundi): {week_start}")
print()

players_data = []

for u in users_rows:
    email, player_name, total_points = u
    
    # Points du jour
    c.execute("""
        SELECT COALESCE(SUM(points), 0), COUNT(*) 
        FROM completed_tasks 
        WHERE user_email=? AND DATE(completed_at, 'localtime')=?
    """, (email, today))
    daily = c.fetchone()
    daily_points = int(daily[0]) if daily[0] else 0
    daily_tasks = int(daily[1]) if daily[1] else 0
    
    # Points de la semaine
    c.execute("""
        SELECT COALESCE(SUM(points), 0), COUNT(*) 
        FROM completed_tasks 
        WHERE user_email=? AND DATE(completed_at, 'localtime') >= ?
    """, (email, week_start))
    weekly = c.fetchone()
    weekly_points = int(weekly[0]) if weekly[0] else 0
    weekly_tasks = int(weekly[1]) if weekly[1] else 0
    
    players_data.append({
        'name': player_name,
        'email': email,
        'total_points': total_points,
        'daily_points': daily_points,
        'daily_tasks': daily_tasks,
        'weekly_points': weekly_points,
        'weekly_tasks': weekly_tasks
    })

# Trier par points de la semaine
players_data.sort(key=lambda x: x['weekly_points'], reverse=True)

print("📊 Classement de la semaine:")
print("-" * 60)
for idx, p in enumerate(players_data, start=1):
    medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
    print(f"{medal} {p['name']:20} | Semaine: {p['weekly_points']:3} pts ({p['weekly_tasks']:2} tâches) | Aujourd'hui: {p['daily_points']:3} pts")

# Vérifier le camembert (répartition par pièce)
print()
print("🏠 Répartition par pièce (semaine):")
print("-" * 60)
c.execute("""
    SELECT category, COUNT(*) as count
    FROM completed_tasks
    WHERE house_id = ?
      AND DATE(completed_at, 'localtime') >= ?
    GROUP BY category
    ORDER BY count DESC
""", (house_id, week_start))

weekly_tasks_by_room = []
total_tasks = 0
for row in c.fetchall():
    category, count = row
    if category:
        weekly_tasks_by_room.append({
            'category': category,
            'count': count
        })
        total_tasks += count

for room in weekly_tasks_by_room:
    percentage = (room['count'] / total_tasks * 100) if total_tasks > 0 else 0
    print(f"{room['category']:25} | {room['count']:3} tâches ({percentage:.1f}%)")

conn.close()

print()
print("=" * 60)
print("✅ Test terminé - Vérifiez que ces données correspondent à l'affichage dans /sats")
