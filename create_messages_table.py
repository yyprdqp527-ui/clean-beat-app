#!/usr/bin/env python3
"""
Script pour créer/mettre à jour la table messages dans la base de données
"""

import sqlite3
import os

DB = "menage.db"

def main():
    print("\n🔧 CRÉATION DE LA TABLE MESSAGES")
    print("="*60)
    
    if not os.path.exists(DB):
        print(f"❌ Erreur: La base de données '{DB}' n'existe pas!")
        return 1
    
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        print(f"\n📁 Base de données: {DB}")
        
        # Vérifier si la table existe déjà
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        exists = c.fetchone() is not None
        
        if exists:
            print("ℹ️  La table 'messages' existe déjà")
            
            # Afficher le nombre d'entrées
            c.execute("SELECT COUNT(*) FROM messages")
            count = c.fetchone()[0]
            print(f"📊 {count} message(s) existant(s)")
        else:
            # Créer la table messages
            print("\n📝 Création de la table messages...")
            
            c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                house_id INTEGER NOT NULL,
                sender_email TEXT,
                sender_type TEXT DEFAULT 'user',
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'chat',
                related_task_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(house_id) REFERENCES houses(id),
                FOREIGN KEY(sender_email) REFERENCES users(email)
            )
            """)
            
            print("✅ Table 'messages' créée !")
        
        # Créer la table message_reads si elle n'existe pas
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_reads'")
        reads_exists = c.fetchone() is not None
        
        if not reads_exists:
            print("\n📝 Création de la table message_reads...")
            
            c.execute("""
            CREATE TABLE IF NOT EXISTS message_reads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(message_id) REFERENCES messages(id),
                FOREIGN KEY(user_email) REFERENCES users(email),
                UNIQUE(message_id, user_email)
            )
            """)
            
            print("✅ Table 'message_reads' créée !")
        
        conn.commit()
        
        # Afficher la structure
        print("\n📋 Structure de la table messages:")
        c.execute("PRAGMA table_info(messages)")
        columns = c.fetchall()
        for col in columns:
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            default = f" DEFAULT {col[4]}" if col[4] else ""
            print(f"  - {col[1]:20} {col[2]:15} {nullable}{default}")
        
        conn.close()
        
        print("\n" + "="*60)
        print("✅ TABLES CRÉÉES AVEC SUCCÈS")
        print("="*60)
        print("\n💡 Les messages de suivi bébé seront maintenant enregistrés")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
