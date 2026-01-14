#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔑 Générateur de clés VAPID pour CleanBeat
Génère les clés nécessaires pour les notifications push
"""

import sys
import json
import os

def generate_vapid_keys():
    """
    Génère une paire de clés VAPID (publique/privée)
    """
    try:
        from pywebpush import webpush
    except ImportError:
        print("❌ Erreur: pywebpush n'est pas installé")
        print("\n📦 Installation requise:")
        print("   pip install pywebpush py-vapid")
        sys.exit(1)
    
    print("=" * 70)
    print("🔑 GÉNÉRATION DES CLÉS VAPID POUR CLEANBEAT")
    print("=" * 70)
    print()
    
    # Générer les clés
    print("⏳ Génération des clés en cours...")
    vapid_keys = webpush.generate_vapid_keys()
    
    private_key = vapid_keys.get('private_key')
    public_key = vapid_keys.get('public_key')
    
    print("✅ Clés générées avec succès !\n")
    
    # Afficher les clés
    print("=" * 70)
    print("📋 CLÉS VAPID")
    print("=" * 70)
    print()
    print("🔒 Clé Privée (VAPID_PRIVATE_KEY):")
    print(f"   {private_key}")
    print()
    print("🔓 Clé Publique (VAPID_PUBLIC_KEY):")
    print(f"   {public_key}")
    print()
    print("=" * 70)
    
    # Instructions
    print()
    print("📝 INSTRUCTIONS DE CONFIGURATION")
    print("=" * 70)
    print()
    print("1️⃣  Copier les variables d'environnement:")
    print()
    print(f'   export VAPID_PRIVATE_KEY="{private_key}"')
    print(f'   export VAPID_PUBLIC_KEY="{public_key}"')
    print()
    print("2️⃣  Ou créer un fichier .env (à ne PAS committer):")
    print()
    print(f'   VAPID_PRIVATE_KEY="{private_key}"')
    print(f'   VAPID_PUBLIC_KEY="{public_key}"')
    print()
    print("3️⃣  Sur macOS/Linux, ajouter dans ~/.zshrc ou ~/.bashrc:")
    print()
    print(f'   export VAPID_PRIVATE_KEY="{private_key}"')
    print(f'   export VAPID_PUBLIC_KEY="{public_key}"')
    print()
    print("   Puis recharger: source ~/.zshrc")
    print()
    print("=" * 70)
    
    # Sauvegarder dans un fichier
    save_file = '.vapid_keys.json'
    keys_data = {
        'private_key': private_key,
        'public_key': public_key,
        'generated_at': __import__('datetime').datetime.now().isoformat()
    }
    
    try:
        with open(save_file, 'w') as f:
            json.dump(keys_data, f, indent=2)
        
        print()
        print(f"💾 Clés sauvegardées dans: {save_file}")
        print()
        print("⚠️  IMPORTANT:")
        print(f"   • Ajoutez '{save_file}' dans votre .gitignore")
        print("   • Ne committez JAMAIS la clé privée dans Git")
        print("   • Gardez ces clés en sécurité")
        print()
        
    except Exception as e:
        print(f"⚠️  Impossible de sauvegarder dans {save_file}: {e}")
    
    # Créer/mettre à jour .gitignore
    gitignore_file = '.gitignore'
    try:
        gitignore_content = ''
        if os.path.exists(gitignore_file):
            with open(gitignore_file, 'r') as f:
                gitignore_content = f.read()
        
        if save_file not in gitignore_content:
            with open(gitignore_file, 'a') as f:
                if gitignore_content and not gitignore_content.endswith('\n'):
                    f.write('\n')
                f.write(f'\n# VAPID keys (secret)\n')
                f.write(f'{save_file}\n')
                f.write('.env\n')
            print(f"✅ Ajouté '{save_file}' dans .gitignore")
        else:
            print(f"✅ '{save_file}' déjà dans .gitignore")
    except Exception as e:
        print(f"⚠️  Impossible de modifier .gitignore: {e}")
    
    print()
    print("=" * 70)
    print("🎉 CONFIGURATION TERMINÉE")
    print("=" * 70)
    print()
    print("🚀 Prochaines étapes:")
    print("   1. Configurer les variables d'environnement")
    print("   2. Redémarrer l'application: python3 app.py")
    print("   3. Ouvrir le menu burger et cliquer sur '🔔 Activer les notifications'")
    print("   4. Accepter la permission quand demandé")
    print()
    print("📚 Plus d'infos: voir NOTIFICATIONS_PUSH_SETUP.md")
    print()

if __name__ == '__main__':
    generate_vapid_keys()
