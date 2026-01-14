#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import date
import time

def test_new_validation():
    """Test d'une nouvelle validation avec le fix appliqué"""
    
    print("🔍 Test de validation APRÈS correction...")
    
    # Utiliser l'utilisateur Monica qui a déjà des points
    email = "hfjhg@me.com"  # Monica
    house_id = 83
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    today = date.today().isoformat()
    
    # Points AVANT
    c.execute("""
        SELECT COALESCE(SUM(points), 0), COUNT(*) 
        FROM completed_tasks 
        WHERE user_email=? AND DATE(completed_at, 'localtime')=?
    """, (email, today))
    
    before_result = c.fetchone()
    points_before = int(before_result[0]) if before_result[0] else 0
    tasks_before = int(before_result[1]) if before_result[1] else 0
    
    print(f"📊 AVANT nouvelle validation:")
    print(f"  Points: {points_before}")
    print(f"  Tâches: {tasks_before}")
    
    # Simuler validation avec le nouveau code
    test_task = f"Test validation fix {int(time.time())}"
    test_points = 4
    
    try:
        # Utiliser la nouvelle requête avec completed_at
        c.execute("""
            INSERT INTO completed_tasks (user_email, house_id, category, task_name, points, completed_at) 
            VALUES (?, ?, 'salon', ?, ?, CURRENT_TIMESTAMP)
        """, (email, house_id, test_task, test_points))
        
        # Mettre à jour points utilisateur
        c.execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE email=?", (test_points, email))
        
        conn.commit()
        print(f"✅ Validation simulée: {test_task} (+{test_points} pts)")
        
    except Exception as e:
        print(f"❌ Erreur validation: {e}")
        conn.close()
        return
    
    # Points APRÈS  
    c.execute("""
        SELECT COALESCE(SUM(points), 0), COUNT(*) 
        FROM completed_tasks 
        WHERE user_email=? AND DATE(completed_at, 'localtime')=?
    """, (email, today))
    
    after_result = c.fetchone()
    points_after = int(after_result[0]) if after_result[0] else 0
    tasks_after = int(after_result[1]) if after_result[1] else 0
    
    print(f"\n📈 APRÈS nouvelle validation:")
    print(f"  Points: {points_after}")
    print(f"  Tâches: {tasks_after}")
    print(f"  📊 Changement: +{points_after - points_before} pts, +{tasks_after - tasks_before} tâches")
    
    if points_after > points_before:
        print("✅ SUCCESS: Les points du jour augmentent correctement!")
        
        # Calculer valeurs template
        pct = points_after
        if pct > 100:
            pct = 100
        fill = 2 if pct > 0 and pct < 2 else pct
        hue = (pct * 120) // 100
        
        print(f"\n🎨 Valeurs template pour Monica:")
        print(f"  current_user_daily_points: {points_after}")
        print(f"  points1: {points_after}")
        print(f"  fill1: {fill}%")
        print(f"  Couleur barre: hue({hue}, 80%, 55%)")
    else:
        print("❌ ÉCHEC: Les points n'ont pas augmenté")
    
    conn.close()

if __name__ == "__main__":
    test_new_validation()