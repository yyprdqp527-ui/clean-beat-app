#!/usr/bin/env python3
"""
Script de test pour vérifier le fonctionnement des points et barres de progression
"""

import sqlite3
import requests
from datetime import date
import json

DB = 'users.db'
BASE_URL = 'http://localhost:8080'

def test_points_system():
    """Test complet du système de points"""
    
    print("🧪 Test du système de points CleanBeat")
    print("=" * 50)
    
    # 1. Vérifier la base de données
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        # Vérifier les utilisateurs existants
        c.execute("SELECT email, points FROM users LIMIT 5")
        users = c.fetchall()
        print(f"📊 Utilisateurs trouvés: {len(users)}")
        for email, points in users:
            print(f"   - {email}: {points or 0} points")
        
        # Vérifier les tâches complétées aujourd'hui
        today = date.today().isoformat()
        c.execute("""
            SELECT user_email, category, task_name, points, completed_at 
            FROM completed_tasks 
            WHERE DATE(completed_at, 'localtime') = ?
            ORDER BY completed_at DESC
            LIMIT 10
        """, (today,))
        
        today_tasks = c.fetchall()
        print(f"\n📅 Tâches complétées aujourd'hui: {len(today_tasks)}")
        for email, cat, task, pts, completed_at in today_tasks:
            print(f"   - {email}: {task} ({cat}) +{pts}pts à {completed_at}")
        
        # Calculer les points du jour par utilisateur
        print(f"\n🏆 Points du jour par utilisateur:")
        c.execute("""
            SELECT user_email, SUM(points), COUNT(*)
            FROM completed_tasks 
            WHERE DATE(completed_at, 'localtime') = ?
            GROUP BY user_email
            ORDER BY SUM(points) DESC
        """, (today,))
        
        daily_stats = c.fetchall()
        for email, total_points, task_count in daily_stats:
            percentage = min(total_points, 100)  # Cap à 100%
            print(f"   - {email}: {total_points} points ({task_count} tâches) -> {percentage}%")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur base de données: {e}")
        return False
    
    # 2. Tester l'endpoint de debug des points
    try:
        print(f"\n🔍 Test de l'endpoint /debug_points...")
        # Note: endpoint nécessite une connexion, donc on s'attend à un 401
        response = requests.get(f"{BASE_URL}/debug_points")
        if response.status_code == 401:
            print("   ✅ Endpoint protégé correctement (401 Unauthorized)")
        else:
            print(f"   ⚠️ Status inattendu: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Erreur endpoint: {e}")
    
    # 3. Vérifier la structure de la page menu
    try:
        print(f"\n📱 Test de la page menu...")
        response = requests.get(f"{BASE_URL}/menu")
        if response.status_code == 200:
            content = response.text
            
            # Vérifier la présence des éléments clés
            checks = [
                ('avatar-col', 'Colonnes d\'avatar'),
                ('vbar', 'Barres de progression'),
                ('avatar-points', 'Points affichés'),
                ('vbar-fill', 'Remplissage des barres'),
                ('data-points', 'Attributs de données points')
            ]
            
            print("   Vérification des éléments du header:")
            for element, description in checks:
                count = content.count(element)
                status = "✅" if count > 0 else "❌"
                print(f"   {status} {description}: {count} occurrences")
            
        else:
            print(f"   ❌ Page menu inaccessible: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Erreur page menu: {e}")
    
    print(f"\n🏁 Test terminé")
    return True

def simulate_task_completion():
    """Simule la complétion d'une tâche pour test"""
    
    print("\n🎯 Simulation d'une validation de tâche")
    print("-" * 40)
    
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        # Prendre un utilisateur existant
        c.execute("SELECT email, house_id FROM users WHERE house_id IS NOT NULL LIMIT 1")
        user_data = c.fetchone()
        
        if not user_data:
            print("❌ Aucun utilisateur avec une maison trouvé")
            conn.close()
            return
        
        email, house_id = user_data
        print(f"👤 Utilisateur test: {email}")
        
        # Points avant
        c.execute("SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at, 'localtime')=?", (email, date.today().isoformat()))
        points_before = c.fetchone()[0]
        
        # Simuler l'ajout d'une tâche test
        test_task = "Test nettoyage cuisine"
        test_points = 5
        
        c.execute("""
            INSERT INTO completed_tasks (user_email, house_id, category, task_name, points) 
            VALUES (?, ?, ?, ?, ?)
        """, (email, house_id, 'cuisine', test_task, test_points))
        
        # Mettre à jour les points utilisateur
        c.execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE email=?", (test_points, email))
        
        conn.commit()
        
        # Points après
        c.execute("SELECT COALESCE(SUM(points),0) FROM completed_tasks WHERE user_email=? AND DATE(completed_at, 'localtime')=?", (email, date.today().isoformat()))
        points_after = c.fetchone()[0]
        
        print(f"📈 Points avant: {points_before}")
        print(f"📈 Points après: {points_after}")
        print(f"➕ Gain: +{points_after - points_before} points")
        print(f"📊 Pourcentage barre: {min(points_after, 100)}%")
        
        # Calculer la couleur HSL pour la barre
        hue = (min(points_after, 100) * 120) // 100
        print(f"🎨 Couleur barre (HSL): hsl({hue}, 80%, 55%)")
        
        conn.close()
        print("✅ Simulation réussie")
        
    except Exception as e:
        print(f"❌ Erreur simulation: {e}")
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    print("🧪 CLEANBEAT - TEST DU SYSTÈME DE POINTS")
    print("=" * 60)
    
    # Test principal
    test_points_system()
    
    # Test de simulation
    simulate_task_completion()
    
    print("\n" + "=" * 60)
    print("💡 Pour tester visuellement:")
    print("   1. Ouvrez http://localhost:8080/menu")
    print("   2. Connectez-vous avec un compte")
    print("   3. Validez une tâche")
    print("   4. Vérifiez que les points et barres se mettent à jour")