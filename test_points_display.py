#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import date

# Test des points pour vérifier l'affichage
def test_points_display():
    print("🔍 Test d'affichage des points...")
    
    # Connexion à la base
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Vérifier les tâches complétées aujourd'hui
    today = date.today().isoformat()
    print(f"📅 Date d'aujourd'hui: {today}")
    
    # Récupérer tous les utilisateurs
    c.execute("SELECT email, name FROM users")
    users = c.fetchall()
    
    print(f"👥 Utilisateurs trouvés: {len(users)}")
    
    for email, name in users:
        print(f"\n👤 {name} ({email}):")
        
        # Points du jour
        c.execute("""
            SELECT COALESCE(SUM(points), 0), COUNT(*) 
            FROM completed_tasks 
            WHERE user_email=? AND DATE(completed_at, 'localtime')=?
        """, (email, today))
        
        daily_result = c.fetchone()
        daily_points = int(daily_result[0]) if daily_result[0] else 0
        daily_tasks = int(daily_result[1]) if daily_result[1] else 0
        
        print(f"  📊 Points du jour: {daily_points}")
        print(f"  ✅ Tâches du jour: {daily_tasks}")
        
        # Points totaux
        c.execute("SELECT COALESCE(SUM(points), 0) FROM completed_tasks WHERE user_email=?", (email,))
        total_points = c.fetchone()[0]
        print(f"  🏆 Points totaux: {total_points}")
        
        # Dernières tâches
        c.execute("""
            SELECT task_name, points, completed_at 
            FROM completed_tasks 
            WHERE user_email=? 
            ORDER BY completed_at DESC 
            LIMIT 3
        """, (email,))
        
        recent_tasks = c.fetchall()
        if recent_tasks:
            print(f"  🔥 Dernières tâches:")
            for task_name, points, completed_at in recent_tasks:
                print(f"    • {task_name}: +{points} pts ({completed_at})")
        else:
            print(f"  ❌ Aucune tâche trouvée")
    
    conn.close()
    print(f"\n✅ Test terminé!")

if __name__ == "__main__":
    test_points_display()