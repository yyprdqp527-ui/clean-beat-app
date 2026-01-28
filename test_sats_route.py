#!/usr/bin/env python3
import sqlite3
from datetime import date

DB = 'users.db'

try:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Tester avec l'utilisateur de test
    test_email = 'agdaval@yahoo.fr'
    
    c.execute('SELECT house_id FROM users WHERE email=?', (test_email,))
    row = c.fetchone()
    
    if row and row[0]:
        house_id = row[0]
        print(f'✅ House ID: {house_id}')
        
        # Tester les requêtes utilisées dans /sats
        c.execute('''
            SELECT email, name, avatar, avatar_url, avatar_file, points 
            FROM users WHERE house_id=?
        ''', (house_id,))
        users_rows = c.fetchall()
        print(f'✅ Nombre d'utilisateurs: {len(users_rows)}')
        
        for u in users_rows:
            print(f'   - {u[1]} ({u[0]})')
            
        # Tester les points hebdomadaires
        from datetime import datetime, timedelta
        monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        
        for user_email, name, *_ in users_rows:
            c.execute('''
                SELECT COALESCE(SUM(points), 0) 
                FROM completed_tasks 
                WHERE user_email=? AND house_id=? AND DATE(completed_at) >= ?
            ''', (user_email, house_id, monday))
            weekly_points = c.fetchone()[0]
            print(f'   📊 {name}: {weekly_points} pts hebdo')
    else:
        print('❌ Pas de maison trouvée')
        
    conn.close()
    print('\n✅ Test réussi - aucune exception levée')
    
except Exception as e:
    print(f'\n❌ Erreur: {e}')
    import traceback
    traceback.print_exc()
