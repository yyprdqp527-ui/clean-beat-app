#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import sqlite3
from datetime import date, datetime
import time

def test_real_task_validation():
    """Test de validation de tâche en temps réel"""
    
    print("🔍 Test de validation de tâche en temps réel...")
    print("⚠️  Attention: Ce test va valider une vraie tâche!")
    
    base_url = "http://192.168.1.156:8080"
    
    # 1. Créer un utilisateur de test ou utiliser un existant
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Vérifier s'il y a un utilisateur récent
    today = date.today().isoformat()
    c.execute("""
        SELECT u.email, u.name, u.house_id
        FROM users u 
        WHERE u.house_id IS NOT NULL
        ORDER BY u.id DESC
        LIMIT 1
    """)
    
    user_row = c.fetchone()
    if not user_row:
        print("❌ Aucun utilisateur trouvé")
        conn.close()
        return
        
    email, name, house_id = user_row
    print(f"👤 Utilisateur test: {name} ({email})")
    print(f"🏠 Maison: {house_id}")
    
    # 2. Vérifier points AVANT
    c.execute("""
        SELECT COALESCE(SUM(points), 0), COUNT(*) 
        FROM completed_tasks 
        WHERE user_email=? AND DATE(completed_at, 'localtime')=?
    """, (email, today))
    
    before_result = c.fetchone()
    points_before = int(before_result[0]) if before_result[0] else 0
    tasks_before = int(before_result[1]) if before_result[1] else 0
    
    print(f"\n📊 AVANT validation:")
    print(f"  Points du jour: {points_before}")
    print(f"  Tâches du jour: {tasks_before}")
    
    # 3. Simuler une session utilisateur (pas de vraie validation via HTTP pour éviter les problèmes d'auth)
    print(f"\n🎯 Simulation de validation d'une tâche de test...")
    
    # Insérer manuellement une tâche pour tester
    test_task_name = f"Test task {int(time.time())}"
    test_points = 5
    
    try:
        c.execute("""
            INSERT INTO completed_tasks (user_email, house_id, category, task_name, points) 
            VALUES (?, ?, 'cuisine', ?, ?)
        """, (email, house_id, test_task_name, test_points))
        
        # Mettre à jour les points utilisateur
        c.execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE email=?", (test_points, email))
        
        conn.commit()
        print(f"✅ Tâche test insérée: {test_task_name} (+{test_points} pts)")
        
    except Exception as e:
        print(f"❌ Erreur insertion: {e}")
        conn.close()
        return
    
    # 4. Vérifier points APRÈS
    c.execute("""
        SELECT COALESCE(SUM(points), 0), COUNT(*) 
        FROM completed_tasks 
        WHERE user_email=? AND DATE(completed_at, 'localtime')=?
    """, (email, today))
    
    after_result = c.fetchone()
    points_after = int(after_result[0]) if after_result[0] else 0
    tasks_after = int(after_result[1]) if after_result[1] else 0
    
    print(f"\n📈 APRÈS validation:")
    print(f"  Points du jour: {points_after}")
    print(f"  Tâches du jour: {tasks_after}")
    print(f"  Différence: +{points_after - points_before} points, +{tasks_after - tasks_before} tâches")
    
    # 5. Simuler les calculs du template
    pct_after = points_after
    if pct_after > 100:
        pct_after = 100
    fill_after = 2 if pct_after > 0 and pct_after < 2 else pct_after
    hue_after = (pct_after * 120) // 100
    
    print(f"\n🎨 Valeurs pour template:")
    print(f"  points1: {points_after}")
    print(f"  pct1: {pct_after}%")
    print(f"  fill1: {fill_after}%")
    print(f"  hue1: {hue_after}")
    
    conn.close()
    
    # 6. Tester l'accès au menu
    print(f"\n🌐 Test d'accès au menu...")
    try:
        # Sans session, on ne peut pas tester l'affichage complet
        # Mais on peut vérifier que la page répond
        response = requests.get(f"{base_url}/menu", timeout=5)
        print(f"📊 Status menu: {response.status_code}")
        
        if response.status_code == 200:
            content_length = len(response.text)
            print(f"✅ Menu accessible ({content_length} chars)")
        else:
            print(f"❌ Problème d'accès au menu")
            
    except Exception as e:
        print(f"❌ Erreur d'accès au menu: {e}")

if __name__ == "__main__":
    test_real_task_validation()