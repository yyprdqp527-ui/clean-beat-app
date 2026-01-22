#!/usr/bin/env python3
"""
Script d'optimisation de la base de données
Nettoie et optimise users.db pour de meilleures performances
"""

import sqlite3
import os

DB = "users.db"

def optimize_database():
    """Optimise la base de données"""
    print("🔧 Optimisation de la base de données...")
    
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    # 1. Activer WAL mode
    cursor.execute('PRAGMA journal_mode=WAL')
    print("✅ Mode WAL activé")
    
    # 2. Analyser et optimiser
    cursor.execute('ANALYZE')
    print("✅ Analyse effectuée")
    
    # 3. VACUUM pour compacter
    cursor.execute('VACUUM')
    print("✅ Base de données compactée")
    
    # 4. Vérifier l'intégrité
    result = cursor.execute('PRAGMA integrity_check').fetchone()
    if result[0] == 'ok':
        print("✅ Intégrité vérifiée : OK")
    else:
        print(f"⚠️  Problème d'intégrité : {result[0]}")
    
    # 5. Afficher les stats
    size_before = os.path.getsize(DB)
    print(f"\n📊 Taille de la base : {size_before / 1024:.1f} KB")
    
    # Compter les enregistrements
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    if 'users' in tables:
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"👥 Utilisateurs : {users_count}")
    
    if 'rewards' in tables:
        cursor.execute("SELECT COUNT(*) FROM rewards")
        rewards_count = cursor.fetchone()[0]
        print(f"🎁 Récompenses : {rewards_count}")
    
    conn.close()
    print("\n✅ Optimisation terminée !")

if __name__ == "__main__":
    optimize_database()
