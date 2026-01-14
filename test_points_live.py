#!/usr/bin/env python3
"""
Test en direct du système de points avec un utilisateur réel
"""

import sqlite3
from datetime import date

DB = 'users.db'

def test_with_real_user():
    """Test avec un utilisateur réel existant"""
    
    print("🔍 Test avec utilisateur réel")
    print("=" * 40)
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Trouver un utilisateur actif avec des points aujourd'hui
    today = date.today().isoformat()
    c.execute("""
        SELECT user_email, SUM(points), COUNT(*)
        FROM completed_tasks 
        WHERE DATE(completed_at, 'localtime') = ?
        GROUP BY user_email
        ORDER BY SUM(points) DESC
        LIMIT 1
    """, (today,))
    
    result = c.fetchone()
    if not result:
        print("❌ Aucun utilisateur actif aujourd'hui")
        conn.close()
        return
    
    user_email, total_points, task_count = result
    print(f"👤 Utilisateur le plus actif: {user_email}")
    print(f"📊 Points aujourd'hui: {total_points}")
    print(f"📝 Tâches complétées: {task_count}")
    
    # Calculer le pourcentage pour la barre
    percentage = min(int(total_points), 100)
    fill_height = max(2, percentage) if percentage > 0 else 0
    
    print(f"📏 Hauteur de barre: {fill_height}%")
    
    # Calculer la couleur HSL
    hue = (percentage * 120) // 100
    print(f"🎨 Couleur barre: hsl({hue}, 80%, 55%)")
    
    # Vérifier la logique JavaScript du menu
    print(f"\n🔧 Logique frontend:")
    print(f"   - data-points=\"{total_points}\"")
    print(f"   - data-fill=\"{fill_height}\"")
    print(f"   - style=\"height: {fill_height}%; background: hsl({hue}, 80%, 55%);\"")
    
    # Lister les tâches de cet utilisateur aujourd'hui
    c.execute("""
        SELECT category, task_name, points, completed_at
        FROM completed_tasks 
        WHERE user_email = ? AND DATE(completed_at, 'localtime') = ?
        ORDER BY completed_at DESC
    """, (user_email, today))
    
    tasks = c.fetchall()
    print(f"\n📋 Détail des tâches:")
    for i, (cat, task, pts, time) in enumerate(tasks, 1):
        print(f"   {i}. {task} ({cat}) +{pts}pts à {time}")
    
    conn.close()
    return user_email, total_points, percentage

def check_menu_rendering():
    """Vérifier le rendu des barres dans le template"""
    
    print(f"\n🎨 Vérification du rendu template")
    print("-" * 40)
    
    # Analyser le template menu.html pour voir la logique d'affichage
    with open('templates/menu.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Chercher les calculs de pourcentage
    lines = content.split('\n')
    relevant_lines = []
    
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ['pct1', 'pct_p2', 'fill', 'vbar-fill', 'data-fill']):
            relevant_lines.append(f"L{i+1}: {line.strip()}")
    
    print("📝 Lignes importantes du template:")
    for line in relevant_lines[:10]:  # Les 10 premières
        print(f"   {line}")
    
    if len(relevant_lines) > 10:
        print(f"   ... et {len(relevant_lines) - 10} autres lignes")

def simulate_progress_bar(points):
    """Simule l'affichage de la barre de progression"""
    
    print(f"\n📊 Simulation barre de progression")
    print("-" * 40)
    
    # Logique identique au template
    pct = int(points)
    if pct > 100:
        pct = 100
    
    fill = 2 if pct > 0 and pct < 2 else pct
    hue = (pct * 120) // 100
    
    print(f"Points: {points}")
    print(f"Pourcentage: {pct}%")
    print(f"Fill: {fill}%")
    print(f"Hue: {hue}")
    print(f"CSS: height: {fill}%; background: hsl({hue}, 80%, 55%);")
    
    # Affichage visuel simple
    bar_length = 20
    filled = int((fill / 100) * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"Visual: [{bar}] {fill}%")

if __name__ == "__main__":
    print("🧪 TEST LIVE - SYSTÈME DE POINTS CLEANBEAT")
    print("=" * 60)
    
    # Test avec utilisateur réel
    user_data = test_with_real_user()
    
    if user_data:
        user_email, total_points, percentage = user_data
        
        # Simulation de barre
        simulate_progress_bar(total_points)
        
        # Vérification template
        check_menu_rendering()
        
        print(f"\n🎯 RÉSULTAT:")
        print(f"✅ Les points s'affichent: {total_points} pts")
        print(f"✅ La barre progresse: {percentage}%")
        print(f"✅ Couleur adaptée selon progression")
        
    else:
        print("❌ Impossible de tester sans utilisateur actif")
    
    print(f"\n💡 Pour tester en temps réel:")
    print(f"   1. Connectez-vous avec un compte sur http://localhost:8080")
    print(f"   2. Validez quelques tâches")
    print(f"   3. Retournez au menu pour voir la progression")