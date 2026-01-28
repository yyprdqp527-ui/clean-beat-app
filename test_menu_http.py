import requests
from bs4 import BeautifulSoup

# Se connecter d'abord pour obtenir une session
session = requests.Session()

# Connexion
login_data = {
    'email': 'agdaval@yahoo.fr',
    'password': '0000'  # Si le mot de passe est différent, mettez le bon
}

print("🔐 Connexion...")
response = session.post('http://127.0.0.1:8000/login', data=login_data, allow_redirects=False)
print(f"   Status: {response.status_code}")
print(f"   Cookies: {session.cookies.get_dict()}")

# Requête vers /menu
print("\n📄 Requête vers /menu...")
response = session.get('http://127.0.0.1:8000/menu')
print(f"   Status: {response.status_code}")
print(f"   Content-Length: {len(response.text)} caractères")

# Parser le HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Vérifier les éléments clés
print("\n🔍 Éléments trouvés:")
house_container = soup.find('div', class_='house-container')
print(f"   ✓ house-container: {'Trouvé' if house_container else '❌ Absent'}")

svg = soup.find('svg', class_='svg-room')
print(f"   ✓ svg-room: {'Trouvé' if svg else '❌ Absent'}")

room_groups = soup.find_all('g', class_='room-group')
print(f"   ✓ room-group: {len(room_groups)} éléments")

modal = soup.find('div', id='house-name-modal')
modal_status = 'Trouvé' if modal else "Absent (c'est normal)"
print(f"   ✓ house-name-modal: {modal_status}")

# Vérifier le body
body = soup.find('body')
if body:
    body_style = body.get('style', '')
    print(f"\n🎨 Style du body: {body_style if body_style else 'Aucun'}")
    print(f"   Contenu body: {len(str(body))} caractères")
    
    # Vérifier s'il y a du contenu visible
    if len(body.get_text(strip=True)) < 100:
        print("   ⚠️ Body presque vide!")
    else:
        print("   ✅ Body contient du texte")

# Afficher un extrait du HTML autour de house-container
if house_container:
    print(f"\n📝 Extrait HTML de house-container:")
    print(str(house_container)[:500] + "...")
else:
    # Afficher les 1000 premiers caractères du body
    print(f"\n📝 Début du body HTML:")
    if body:
        print(str(body)[:1000] + "...")
