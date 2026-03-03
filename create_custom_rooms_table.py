#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour créer la table custom_rooms pour les pièces personnalisables
"""

import sqlite3
import os

# Chemin vers la base de données
db_path = os.path.join(os.path.dirname(__file__), 'users.db')

def create_custom_rooms_table():
    """Crée la table custom_rooms si elle n'existe pas"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Créer la table custom_rooms
        c.execute('''
            CREATE TABLE IF NOT EXISTS custom_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                room_type TEXT NOT NULL,
                custom_name TEXT,
                position INTEGER DEFAULT 0,
                image_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        
        # Index pour optimiser les requêtes
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_custom_rooms_user 
            ON custom_rooms(user_email)
        ''')
        
        conn.commit()
        print("✅ Table custom_rooms créée avec succès !")
        
        # Afficher la structure
        c.execute("PRAGMA table_info(custom_rooms)")
        columns = c.fetchall()
        print("\n📋 Structure de la table custom_rooms:")
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de la table: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    create_custom_rooms_table()
