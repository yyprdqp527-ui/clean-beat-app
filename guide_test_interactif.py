#!/usr/bin/env python3
"""
Guide interactif pour tester le système de suivi bébé
"""

import sqlite3
import sys

DB = "menage.db"

def main():
    print("\n" + "="*70)
    print("  🍼 GUIDE DE TEST - SYSTÈME DE SUIVI BÉBÉ 👶")
    print("="*70)
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Vérifier qu'il y a des utilisateurs
    c.execute("SELECT email, name, house_id FROM users WHERE house_id IS NOT NULL LIMIT 1")
    user = c.fetchone()
    
    if not user:
        print("\n❌ Aucun utilisateur trouvé avec une maison")
        print("   Veuillez d'abord créer un compte et rejoindre une maison")
        conn.close()
        return 1
    
    user_email, user_name, house_id = user
    
    # Afficher les infos
    print(f"\n✅ Utilisateur trouvé: {user_name} ({user_email})")
    print(f"✅ Maison ID: {house_id}")
    
    # Vérifier l'état actuel
    c.execute("SELECT COUNT(*) FROM messages")
    msg_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM baby_tracking")
    baby_count = c.fetchone()[0]
    
    print(f"\n📊 État actuel de la base de données:")
    print(f"   Messages totaux: {msg_count}")
    print(f"   Suivis bébé: {baby_count}")
    
    if msg_count == 0:
        print("\n" + "="*70)
        print("  ⚠️  AUCUN MESSAGE - VOICI COMMENT TESTER")
        print("="*70)
        print("""
📝 ÉTAPES POUR CRÉER UN MESSAGE DE SUIVI BÉBÉ :

1. 🌐 Ouvrir votre navigateur et aller sur l'application
   URL : http://localhost:8000
   (ou votre adresse IP locale si vous utilisez un mobile)

2. 🔐 Se connecter avec votre compte
   Email : ag@me.com (ou votre email)

3. 🏠 Depuis le menu principal, cliquer sur "Ch. Bébé"
   (c'est la chambre bébé dans la maison)

4. 🍼 Cliquer sur "Donner le biberon" (ou "Changer les couches")

5. 📋 Un formulaire apparaît avec :
   ⏰ Heure : Choisir une heure (ex: 14:30)
   🍼 Quantité (ml) : Entrer 180
   📝 Observations : "bébé a bien bu" (optionnel pour biberon)

6. 👤 Sélectionner un joueur (cliquer sur votre avatar)

7. ✅ Le message "Tâche validée !" apparaît

8. 💬 ALLER DANS LA MESSAGERIE :
   - Cliquer sur le menu burger (☰) en haut à droite
   - Cliquer sur "Messagerie" (icône 💬)
   
   OU
   
   - Aller directement sur : http://localhost:8000/comments

9. 📨 Vous devriez voir un message rose :
   "🍼 Anne-gaëlle a donné le biberon à 14:30 (180 ml)
    📝 bébé a bien bu"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 ASTUCE : La messagerie se trouve dans le menu burger (☰)
           en haut à droite de l'écran !
""")
        
        # Proposer de créer un message de test
        print("\n" + "="*70)
        choice = input("Voulez-vous que je crée un message de TEST ? [o/N] ")
        
        if choice.lower() == 'o':
            # Créer un message de test
            from datetime import datetime
            
            tracking_time = "14:30"
            bottle_ml = 180
            observations = "TEST AUTOMATIQUE - bébé a bien bu 🍼"
            
            # Insérer dans baby_tracking
            c.execute("""
                INSERT INTO baby_tracking (user_email, house_id, task_type, tracking_time, bottle_ml, observations)
                VALUES (?, ?, 'biberon', ?, ?, ?)
            """, (user_email, house_id, tracking_time, bottle_ml, observations))
            
            # Créer le message
            c.execute("SELECT house_name, name FROM houses WHERE id=?", (house_id,))
            house_row = c.fetchone()
            sender_name = house_row[0] if house_row and house_row[0] else (house_row[1] if house_row else "Maison")
            
            message_text = f"🍼 {user_name} a donné le biberon à {tracking_time} ({bottle_ml} ml)\n📝 {observations}"
            
            c.execute("""
                INSERT INTO messages (house_id, sender_email, sender_type, content, message_type)
                VALUES (?, ?, 'house', ?, 'baby_tracking')
            """, (house_id, sender_name, message_text))
            
            conn.commit()
            
            print("\n✅ Message de TEST créé avec succès !")
            print(f"\n📨 Contenu du message :")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(message_text)
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("\n🌐 MAINTENANT, ALLEZ VOIR LA MESSAGERIE :")
            print("   1. Ouvrir : http://localhost:8000/comments")
            print("   2. Ou cliquer sur le menu burger (☰) > Messagerie")
            print("\n   Le message devrait apparaître en ROSE 🩷")
    else:
        print(f"\n✅ Il y a déjà {msg_count} message(s)")
        print("\n📨 Derniers messages :")
        
        c.execute("""
            SELECT id, sender_email, content, message_type, timestamp
            FROM messages
            ORDER BY id DESC
            LIMIT 3
        """)
        
        for row in c.fetchall():
            msg_id, sender, content, msg_type, timestamp = row
            print(f"\n  [{msg_id}] Type: {msg_type}")
            print(f"  De: {sender}")
            print(f"  Contenu: {content[:80]}{'...' if len(content) > 80 else ''}")
        
        print("\n🌐 Pour voir tous les messages, allez sur :")
        print("   http://localhost:8000/comments")
    
    conn.close()
    
    print("\n" + "="*70)
    print("  📞 BESOIN D'AIDE ?")
    print("="*70)
    print("""
Si vous ne voyez toujours pas les messages :

1. Vérifiez que vous êtes connecté avec le bon compte
2. Vérifiez que vous êtes sur la page /comments (messagerie)
3. Essayez de rafraîchir la page (Cmd+R ou F5)
4. Vérifiez les logs du serveur pour voir les erreurs

Le serveur affiche des logs comme :
  [DEBUG COMMENTS] house_id=154, current_user=ag@me.com
  """)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
