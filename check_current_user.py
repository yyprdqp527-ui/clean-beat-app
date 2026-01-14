#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import sqlite3

def check_current_user():
    """Test qui est l'utilisateur connecté sur l'IP qui effectue des tâches"""
    
    print("🔍 Test de l'utilisateur actuel...")
    
    # Essayer de récupérer des infos depuis debug_points endpoint
    try:
        response = requests.get('http://192.168.1.156:8080/debug_points', timeout=10)
        print(f"📡 Réponse debug_points: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Données debug: {data}")
        else:
            print(f"❌ Erreur debug_points: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur connexion debug_points: {e}")

def show_recent_users():
    """Afficher les utilisateurs avec activité récente"""
    print("\n📈 Utilisateurs avec activité récente:")
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Récupérer les utilisateurs avec points aujourd'hui
    c.execute("""
        SELECT DISTINCT u.email, u.name, u.house_id
        FROM users u 
        JOIN completed_tasks ct ON u.email = ct.user_email
        WHERE DATE(ct.completed_at, 'localtime') = '2025-12-04'
        ORDER BY ct.completed_at DESC
    """)
    
    recent_users = c.fetchall()
    
    for email, name, house_id in recent_users:
        print(f"👤 {name} ({email}) - Maison ID: {house_id}")
        
        # Vérifier les tâches d'aujourd'hui
        c.execute("""
            SELECT task_name, points, completed_at
            FROM completed_tasks
            WHERE user_email = ? AND DATE(completed_at, 'localtime') = '2025-12-04'
            ORDER BY completed_at DESC
        """, (email,))
        
        today_tasks = c.fetchall()
        total_today = sum(task[1] for task in today_tasks)
        
        print(f"   📊 Total aujourd'hui: {total_today} points")
        print(f"   ✅ Tâches: {len(today_tasks)}")
        
        for task_name, points, completed_at in today_tasks[:3]:  # Montrer les 3 dernières
            print(f"     • {task_name}: +{points} pts ({completed_at})")
    
    conn.close()

if __name__ == "__main__":
    check_current_user()
    show_recent_users()