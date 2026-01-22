#!/usr/bin/env python3
"""
Script pour afficher les informations de connexion CleanBeat
Génère un QR code pour connexion rapide depuis mobile
"""

import socket
import subprocess
import sys

def get_local_ip():
    """Récupère l'adresse IP locale"""
    try:
        # Méthode 1 : Via socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # Méthode 2 : Via ifconfig
        try:
            result = subprocess.run(['ipconfig', 'getifaddr', 'en0'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            
            result = subprocess.run(['ipconfig', 'getifaddr', 'en1'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
    return None

def generate_qr_code(url):
    """Génère un QR code dans le terminal"""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=1, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        return True
    except ImportError:
        return False

def main():
    port = 8000
    ip = get_local_ip()
    
    print("\n" + "="*60)
    print("📱 CleanBeat - Accès Multi-Appareils")
    print("="*60 + "\n")
    
    if not ip:
        print("❌ Impossible de détecter l'adresse IP")
        print("💡 Vérifiez que vous êtes connecté au WiFi\n")
        return 1
    
    url = f"http://{ip}:{port}"
    
    print("🌐 Adresses de connexion:")
    print(f"   • Sur cet ordinateur : http://localhost:{port}")
    print(f"   • Depuis autres appareils : {url}\n")
    
    print("📱 Instructions par appareil:")
    print("\n📱 iPhone/iPad:")
    print(f"   1. Ouvrir Safari")
    print(f"   2. Taper : {url}")
    print(f"   3. Bouton Partager → 'Sur l'écran d'accueil'")
    
    print("\n🤖 Android:")
    print(f"   1. Ouvrir Chrome")
    print(f"   2. Taper : {url}")
    print(f"   3. Menu (⋮) → 'Ajouter à l'écran d'accueil'")
    
    print("\n💻 Autre ordinateur:")
    print(f"   1. Ouvrir n'importe quel navigateur")
    print(f"   2. Taper : {url}")
    
    print("\n" + "="*60)
    print("⚠️  IMPORTANT")
    print("="*60)
    print("✓ Tous les appareils doivent être sur le MÊME WiFi")
    print("✓ Le serveur doit être actif (python3 app.py)")
    print("✓ Cette adresse peut changer si vous redémarrez le WiFi")
    
    # Tenter de générer un QR code
    print("\n" + "="*60)
    has_qr = generate_qr_code(url)
    if has_qr:
        print("📷 Scannez ce QR code avec votre téléphone!")
        print("="*60)
    else:
        print("💡 Pour un QR code : pip3 install qrcode[pil]")
        print("="*60)
    
    print(f"\n✨ URL à partager : {url}\n")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
