#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import date, datetime

def test_task_completion_flow():
    """Test du flow complet de validation d'une tâche"""
    
    print("🔍 Test du flow de validation de tâche...")
    
    # Connexion à la base
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    today = date.today().isoformat()
    
    # Trouver l'utilisateur actif le plus récent
    c.execute("""
        SELECT u.email, u.name, u.house_id
        FROM users u 
        JOIN completed_tasks ct ON u.email = ct.user_email
        WHERE DATE(ct.completed_at, 'localtime') = ?
        ORDER BY ct.completed_at DESC
        LIMIT 1
    """, (today,))
    
    user_row = c.fetchone()
    if not user_row:
        print("❌ Aucun utilisateur actif trouvé aujourd'hui")
        conn.close()
        return
    
    email, name, house_id = user_row
    print(f"👤 Utilisateur testé: {name} ({email})")
    print(f"🏠 Maison ID: {house_id}")
    
    # Vérifier points AVANT
    print(f"\n📊 AVANT validation (situation actuelle):")
    
    # Points du jour
    c.execute("""
        SELECT COALESCE(SUM(points), 0), COUNT(*) 
        FROM completed_tasks 
        WHERE user_email=? AND DATE(completed_at, 'localtime')=?
    """, (email, today))
    
    daily_result = c.fetchone()
    daily_points_before = int(daily_result[0]) if daily_result[0] else 0
    daily_tasks_before = int(daily_result[1]) if daily_result[1] else 0
    
    print(f"  📈 Points du jour: {daily_points_before}")
    print(f"  ✅ Tâches du jour: {daily_tasks_before}")
    
    # Calculer le pourcentage et fill pour les barres
    pct_before = daily_points_before
    if pct_before > 100:
        pct_before = 100
    fill_before = 2 if pct_before > 0 and pct_before < 2 else pct_before
    hue_before = (pct_before * 120) // 100
    
    print(f"  📊 Pourcentage calculé: {pct_before}%")
    print(f"  🎨 Fill barre: {fill_before}%")
    print(f"  🌈 Hue couleur: {hue_before}")
    
    # Vérifier les joueurs de la maison
    print(f"\n👥 Joueurs de la maison {house_id}:")
    c.execute("SELECT email, name FROM users WHERE house_id=?", (house_id,))
    house_members = c.fetchall()
    
    for member_email, member_name in house_members:
        c.execute("""
            SELECT COALESCE(SUM(points), 0) 
            FROM completed_tasks 
            WHERE user_email=? AND DATE(completed_at, 'localtime')=?
        """, (member_email, today))
        
        member_points = c.fetchone()[0] or 0
        marker = " 👈 VOUS" if member_email == email else ""
        print(f"  • {member_name}: {member_points} points{marker}")
    
    # Dernières tâches
    print(f"\n🔥 3 dernières tâches de {name}:")
    c.execute("""
        SELECT task_name, points, completed_at
        FROM completed_tasks
        WHERE user_email=?
        ORDER BY completed_at DESC
        LIMIT 3
    """, (email,))
    
    recent_tasks = c.fetchall()
    for task_name, points, completed_at in recent_tasks:
        print(f"  • {task_name}: +{points} pts ({completed_at})")
    
    conn.close()

def verify_menu_template():
    """Vérifier que le template menu utilise bien current_user_daily_points"""
    print(f"\n🔍 Vérification template menu...")
    
    try:
        with open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html', 'r') as f:
            content = f.read()
            
        # Rechercher les variables importantes
        if 'current_user_daily_points' in content:
            print("✅ current_user_daily_points trouvé dans le template")
        else:
            print("❌ current_user_daily_points MANQUANT dans le template")
            
        if 'points1 = current_user_daily_points' in content:
            print("✅ Assignation points1 correcte")
        else:
            print("❌ Assignation points1 incorrecte")
            
        # Compter les occurrences
        points1_count = content.count('{{ points1 }}')
        fill1_count = content.count('{{ fill1 }}')
        
        print(f"📊 Occurrences {{ points1 }}: {points1_count}")
        print(f"📊 Occurrences {{ fill1 }}: {fill1_count}")
        
    except Exception as e:
        print(f"❌ Erreur lecture template: {e}")

if __name__ == "__main__":
    test_task_completion_flow()
    verify_menu_template()