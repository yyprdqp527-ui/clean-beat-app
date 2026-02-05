#!/usr/bin/env python3
"""
Script pour créer/mettre à jour la table baby_tracking dans la base de données
"""

import sqlite3
import os

DB = "menage.db"

def main():
    print("\n🔧 MISE À JOUR DE LA BASE DE DONNÉES")
    print("="*60)
    
    if not os.path.exists(DB):
        print(f"❌ Erreur: La base de données '{DB}' n'existe pas!")
        return 1
    
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        print(f"\n📁 Base de données: {DB}")
        
        # Vérifier si la table existe déjà
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='baby_tracking'")
        exists = c.fetchone() is not None
        
        if exists:
            print("ℹ️  La table 'baby_tracking' existe déjà")
            
            # Afficher le nombre d'entrées
            c.execute("SELECT COUNT(*) FROM baby_tracking")
            count = c.fetchone()[0]
            print(f"📊 {count} entrée(s) existante(s)")
            
            choice = input("\n⚠️  Voulez-vous recréer la table (SUPPRIMERA les données) ? [o/N] ")
            if choice.lower() != 'o':
                print("✅ Opération annulée")
                conn.close()
                return 0
            
            # Supprimer l'ancienne table
            c.execute("DROP TABLE baby_tracking")
            print("🗑️  Ancienne table supprimée")
        
        # Créer la table
        print("\n📝 Création de la table baby_tracking...")
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS baby_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            house_id INTEGER NOT NULL,
            task_type TEXT NOT NULL,
            tracking_time TEXT NOT NULL,
            bottle_ml INTEGER,
            observations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_email) REFERENCES users(email),
            FOREIGN KEY(house_id) REFERENCES houses(id)
        )
        """)
        
        conn.commit()
        
        print("✅ Table 'baby_tracking' créée avec succès!")
        
        # Afficher la structure
        print("\n📋 Structure de la table:")
        c.execute("PRAGMA table_info(baby_tracking)")
        columns = c.fetchall()
        for col in columns:
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            print(f"  - {col[1]:20} {col[2]:15} {nullable}")
        
        conn.close()
        
        print("\n" + "="*60)
        print("✅ MISE À JOUR TERMINÉE AVEC SUCCÈS")
        print("="*60)
        print("\n💡 Vous pouvez maintenant tester le système de suivi bébé")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
