# 💰 STRATÉGIE PUBLICITAIRE MALIGNE
## Monétiser sans dégrader l'expérience utilisateur

---

## 🎯 PRINCIPE FONDAMENTAL

**"La pub doit être UTILE, pas intrusive"**

❌ PAS de pop-ups agressifs  
❌ PAS de vidéos auto-play  
❌ PAS de bannières clignotantes  
✅ OUI à la recommandation contextuelle  
✅ OUI au sponsoring élégant  
✅ OUI à l'affiliation native  

---

## 💡 STRATÉGIE 1 : AFFILIATION AMAZON CONTEXTUELLE

### Concept
Recommander des **produits pertinents** au moment opportun dans le parcours utilisateur.

### Mise en œuvre

```python
# products_recommandation.py

AMAZON_PRODUCTS = {
    'cuisine': [
        {
            'task': 'Faire la vaisselle',
            'products': [
                {
                    'name': 'Liquide vaisselle ultra-concentré Pril',
                    'image': 'pril_liquide.jpg',
                    'price': '4,99€',
                    'rating': 4.7,
                    'reviews': 2453,
                    'affiliate_link': 'https://amzn.to/abc123',
                    'tagline': '💧 3x plus efficace, recommandé par 95% des utilisateurs',
                    'bonus_points': 5
                },
                {
                    'name': 'Éponges grattantes durables',
                    'image': 'eponges_pro.jpg',
                    'price': '7,99€ (pack 10)',
                    'rating': 4.8,
                    'reviews': 1829,
                    'affiliate_link': 'https://amzn.to/def456',
                    'tagline': '🧽 Durent 3x plus longtemps',
                    'bonus_points': 5
                }
            ]
        },
        {
            'task': 'Nettoyer la cuisine',
            'products': [
                {
                    'name': 'Spray nettoyant multi-surfaces',
                    'image': 'spray_cuisine.jpg',
                    'price': '5,99€',
                    'rating': 4.6,
                    'reviews': 3201,
                    'affiliate_link': 'https://amzn.to/ghi789',
                    'tagline': '✨ Désinfecte + fait briller',
                    'bonus_points': 5
                }
            ]
        }
    ],
    'salle_bain': [
        {
            'task': 'Nettoyer la salle de bain',
            'products': [
                {
                    'name': 'Nettoyant calcaire puissant',
                    'image': 'anticalcaire.jpg',
                    'price': '6,49€',
                    'rating': 4.9,
                    'reviews': 4521,
                    'affiliate_link': 'https://amzn.to/jkl012',
                    'tagline': '💎 Chrome éclatant en 30 secondes',
                    'bonus_points': 5
                }
            ]
        }
    ],
    'buanderie': [
        {
            'task': 'Faire la lessive',
            'products': [
                {
                    'name': 'Lessive liquide Ariel Pods 3en1',
                    'image': 'ariel_pods.jpg',
                    'price': '12,99€ (50 doses)',
                    'rating': 4.8,
                    'reviews': 8932,
                    'affiliate_link': 'https://amzn.to/mno345',
                    'tagline': '🌿 Efficace même à froid, écolo',
                    'bonus_points': 10
                }
            ]
        }
    ],
    'salon': [
        {
            'task': 'Passer l\'aspirateur',
            'products': [
                {
                    'name': 'Aspirateur sans fil Dyson V11',
                    'image': 'dyson_v11.jpg',
                    'price': '449€',
                    'rating': 4.9,
                    'reviews': 12453,
                    'affiliate_link': 'https://amzn.to/pqr678',
                    'tagline': '⚡ 60 min d\'autonomie, technologie cyclone',
                    'bonus_points': 50
                }
            ]
        }
    ]
}


def get_product_recommendation(category, task_name):
    """Retourne un produit recommandé pour une tâche"""
    import random
    
    category_products = AMAZON_PRODUCTS.get(category, [])
    
    for task_group in category_products:
        if task_name in task_group['task']:
            products = task_group['products']
            return random.choice(products) if products else None
    
    return None


def track_affiliate_click(user_email, product_name, task, affiliate_link):
    """Track les clics pour analytics"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS affiliate_clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        product_name TEXT,
        task TEXT,
        affiliate_link TEXT,
        clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''INSERT INTO affiliate_clicks 
                (user_email, product_name, task, affiliate_link)
                VALUES (?, ?, ?, ?)''',
             (user_email, product_name, task, affiliate_link))
    
    conn.commit()
    conn.close()
```

### Intégration dans la page tâche

```html
<!-- À ajouter dans templates/task_page.html -->

<!-- Après le bouton de validation -->
{% set product = get_product_recommendation(category, task_name) %}
{% if product %}
<div class="product-recommendation" style="
    max-width: 500px;
    margin: 40px auto 20px;
    background: linear-gradient(135deg, #FFF5E1 0%, #FFF8DC 100%);
    border: 2px solid #FFD700;
    border-radius: 24px;
    padding: 24px;
    box-shadow: 0 8px 24px rgba(255, 215, 0, 0.2);
">
    <div style="text-align: center; color: #8B7355; font-weight: 700; font-size: 14px; margin-bottom: 16px; letter-spacing: 0.5px;">
        💡 RECOMMANDÉ POUR CETTE TÂCHE
    </div>
    
    <div style="display: flex; gap: 16px; align-items: center;">
        <!-- Image produit -->
        <div style="flex: 0 0 100px;">
            <img src="{{ url_for('static', filename='products/' ~ product.image) }}" 
                 alt="{{ product.name }}"
                 style="width: 100%; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        </div>
        
        <!-- Infos produit -->
        <div style="flex: 1;">
            <h4 style="margin: 0 0 8px 0; color: #2C3E50; font-size: 16px; font-weight: 800;">
                {{ product.name }}
            </h4>
            
            <div style="margin-bottom: 8px; color: #666; font-size: 13px; line-height: 1.4;">
                {{ product.tagline }}
            </div>
            
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <span style="color: #FFA500; font-size: 16px;">
                    {{ '⭐' * (product.rating|int) }}{{ '☆' * (5 - product.rating|int) }}
                </span>
                <span style="color: #888; font-size: 12px;">
                    ({{ product.reviews }} avis)
                </span>
            </div>
            
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                <div style="font-size: 22px; font-weight: 800; color: #E74C3C;">
                    {{ product.price }}
                </div>
                
                <a href="{{ product.affiliate_link }}" 
                   target="_blank"
                   onclick="trackAffiliateClick('{{ product.name }}', '{{ task_name }}', '{{ product.affiliate_link }}')"
                   style="
                    background: linear-gradient(135deg, #3498DB 0%, #2980B9 100%);
                    color: white;
                    padding: 10px 20px;
                    border-radius: 20px;
                    text-decoration: none;
                    font-weight: 700;
                    font-size: 14px;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
                    transition: all 0.3s ease;
                " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(52, 152, 219, 0.5)'"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(52, 152, 219, 0.3)'">
                    Voir sur Amazon →
                </a>
            </div>
            
            {% if product.bonus_points > 0 %}
            <div style="
                margin-top: 12px;
                padding: 8px 12px;
                background: linear-gradient(135deg, #FDAE54 0%, #F4C68D 100%);
                border-radius: 12px;
                color: #153036;
                font-weight: 700;
                font-size: 13px;
                text-align: center;
            ">
                🎁 +{{ product.bonus_points }} points bonus si tu l'achètes !
            </div>
            {% endif %}
        </div>
    </div>
</div>

<script>
function trackAffiliateClick(productName, task, link) {
    fetch('/track_affiliate_click', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            product: productName,
            task: task,
            link: link
        })
    });
}
</script>
{% endif %}
```

**Résultat attendu :**
- Taux de clic : 8-12%
- Conversion : 3-5%
- Revenu par clic : 0,50€ - 1,50€

---

## 🔥 STRATÉGIE 2 : SPONSORING DE TÂCHES

### Concept
Les marques parrainent des tâches spécifiques avec **points bonus**.

### Exemple : Semaine Ariel

```python
# sponsored_tasks.py

CURRENT_SPONSORSHIP = {
    'sponsor': 'Ariel',
    'logo': 'ariel_logo.png',
    'color': '#0066CC',
    'duration': {
        'start': '2025-12-15',
        'end': '2025-12-21'
    },
    'sponsored_tasks': [
        {
            'category': 'buanderie',
            'task': 'Faire la lessive',
            'bonus_points': 15,
            'message': '👕 Tâche sponsorisée par Ariel',
            'badge': {
                'name': 'Maître Lessive Ariel',
                'emoji': '👔',
                'condition': '5 lessives pendant la semaine'
            }
        }
    ],
    'promo_code': 'CLEANBEAT20',
    'product_link': 'https://amzn.to/ariel-pods'
}


def is_task_sponsored(category, task_name):
    """Vérifie si une tâche est actuellement sponsorisée"""
    from datetime import datetime
    
    sponsor = CURRENT_SPONSORSHIP
    now = datetime.now().strftime('%Y-%m-%d')
    
    if now < sponsor['duration']['start'] or now > sponsor['duration']['end']:
        return None
    
    for sponsored in sponsor['sponsored_tasks']:
        if sponsored['category'] == category and task_name in sponsored['task']:
            return {
                'sponsor': sponsor['sponsor'],
                'logo': sponsor['logo'],
                'bonus': sponsored['bonus_points'],
                'message': sponsored['message'],
                'color': sponsor['color']
            }
    
    return None
```

### Affichage dans l'interface

```html
<!-- Badge sur la vignette de tâche dans tasks.html -->
{% set sponsor = is_task_sponsored(category, task_name) %}
{% if sponsor %}
<div class="sponsored-badge" style="
    position: absolute;
    top: -8px;
    left: 50%;
    transform: translateX(-50%);
    background: {{ sponsor.color }};
    color: white;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 800;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    white-space: nowrap;
    animation: sponsorPulse 2s ease-in-out infinite;
">
    <img src="{{ url_for('static', filename='sponsors/' ~ sponsor.logo) }}" 
         style="height: 14px; vertical-align: middle; margin-right: 4px;">
    +{{ sponsor.bonus }} PTS BONUS
</div>

<style>
@keyframes sponsorPulse {
    0%, 100% { transform: translateX(-50%) scale(1); }
    50% { transform: translateX(-50%) scale(1.05); }
}
</style>
{% endif %}
```

**Modèle économique :**
- Tarif sponsor : 200-500€/semaine
- ROI marque : Visibilité + Engagement
- Votre bénéfice : 200€+ / campagne

---

## 🎁 STRATÉGIE 3 : PROGRAMME AFFILIATION MALIN

### Concept
Chaque catégorie a ses **produits phares** avec affiliation automatique.

```python
# affiliate_system.py

CATEGORY_PARTNERS = {
    'cuisine': {
        'amazon_search': 'ustensiles+cuisine',
        'featured_products': [
            'Liquide vaisselle',
            'Éponges',
            'Spray nettoyant',
            'Torchons microfibre'
        ]
    },
    'salle_bain': {
        'amazon_search': 'nettoyant+salle+bain',
        'featured_products': [
            'Anti-calcaire',
            'Nettoyant WC',
            'Brosse toilettes',
            'Produits douche'
        ]
    },
    'buanderie': {
        'amazon_search': 'lessive+entretien',
        'featured_products': [
            'Lessive pods',
            'Assouplissant',
            'Détachant',
            'Panier à linge'
        ]
    },
    'salon': {
        'amazon_search': 'aspirateur+rangement',
        'featured_products': [
            'Aspirateur',
            'Lingettes dépoussiérage',
            'Rangements modulables',
            'Diffuseur parfum'
        ]
    }
}


def generate_affiliate_link(category, product_name):
    """Génère un lien d'affiliation Amazon"""
    # Votre TAG d'affiliation Amazon
    AFFILIATE_TAG = 'cleanbeat-21'
    
    # Recherche du produit
    search_query = product_name.replace(' ', '+')
    base_url = f'https://www.amazon.fr/s?k={search_query}'
    
    return f'{base_url}&tag={AFFILIATE_TAG}'
```

### Widget "Boutique" par catégorie

```html
<!-- Section boutique dans tasks.html -->
<div class="category-shop" style="
    max-width: 900px;
    margin: 40px auto;
    background: white;
    border-radius: 24px;
    padding: 30px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
">
    <h3 style="text-align: center; color: #2C3E50; margin-bottom: 20px; font-size: 22px;">
        🛒 Produits recommandés pour {{ category|capitalize }}
    </h3>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
        {% for product in CATEGORY_PARTNERS[category]['featured_products'] %}
        <a href="{{ generate_affiliate_link(category, product) }}" 
           target="_blank"
           style="
            display: block;
            background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            text-decoration: none;
            color: #2C3E50;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        " onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 20px rgba(0,0,0,0.12)'"
           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.05)'">
            <div style="font-size: 40px; margin-bottom: 10px;">🛍️</div>
            <div style="font-weight: 700; font-size: 15px; margin-bottom: 8px;">{{ product }}</div>
            <div style="
                background: linear-gradient(135deg, #3498DB 0%, #2980B9 100%);
                color: white;
                padding: 6px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 700;
                display: inline-block;
            ">
                Voir sur Amazon
            </div>
        </a>
        {% endfor %}
    </div>
    
    <div style="text-align: center; margin-top: 20px; color: #888; font-size: 12px;">
        💡 En achetant via ces liens, tu soutiens CleanBeat ! (sans surcoût)
    </div>
</div>
```

---

## 📊 STRATÉGIE 4 : MODÈLE FREEMIUM

### Version Gratuite (80% des features)
```
✅ Jusqu'à 2 joueurs
✅ Toutes les tâches standards
✅ Badges basiques
✅ Stats basiques
✅ Défis hebdomadaires
⚠️ Avec publicités élégantes
```

### Version Premium (2,99€/mois)
```
🌟 Jusqu'à 6 joueurs (famille)
🎨 Avatars personnalisés illimités
🏆 Badges exclusifs dorés
📊 Stats avancées + graphiques
🎯 Défis personnalisés
🔔 Notifications push
🚫 SANS publicité
🎁 Récompenses premium exclusives
📱 App mobile dédiée (à venir)
```

### Page de conversion

```html
<!-- templates/premium_upgrade.html -->
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>CleanBeat Premium</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .premium-box {
            background: white;
            border-radius: 32px;
            max-width: 600px;
            padding: 50px 40px;
            box-shadow: 0 20px 80px rgba(0,0,0,0.2);
        }
        
        .premium-header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .premium-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        
        .premium-title {
            font-size: 36px;
            font-weight: 800;
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .premium-subtitle {
            font-size: 18px;
            color: #666;
        }
        
        .features-grid {
            display: grid;
            gap: 16px;
            margin-bottom: 40px;
        }
        
        .feature-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px;
            background: #F8F9FA;
            border-radius: 16px;
        }
        
        .feature-icon {
            font-size: 28px;
        }
        
        .feature-text {
            flex: 1;
            font-weight: 600;
            color: #2C3E50;
        }
        
        .pricing {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .price-tag {
            font-size: 48px;
            font-weight: 800;
            color: #2C3E50;
            margin-bottom: 10px;
        }
        
        .price-period {
            font-size: 16px;
            color: #888;
        }
        
        .cta-button {
            width: 100%;
            padding: 20px;
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
            border: none;
            border-radius: 20px;
            font-size: 20px;
            font-weight: 800;
            color: #2C3E50;
            cursor: pointer;
            box-shadow: 0 8px 24px rgba(255, 215, 0, 0.4);
            transition: all 0.3s ease;
        }
        
        .cta-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 32px rgba(255, 215, 0, 0.6);
        }
        
        .guarantee {
            text-align: center;
            margin-top: 20px;
            color: #888;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="premium-box">
        <div class="premium-header">
            <div class="premium-icon">👑</div>
            <h1 class="premium-title">CleanBeat Premium</h1>
            <p class="premium-subtitle">L'expérience ultime pour toute la famille</p>
        </div>
        
        <div class="features-grid">
            <div class="feature-item">
                <span class="feature-icon">👨‍👩‍👧‍👦</span>
                <span class="feature-text">Jusqu'à 6 joueurs (toute la famille !)</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">🎨</span>
                <span class="feature-text">Avatars personnalisés illimités</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">🏆</span>
                <span class="feature-text">Badges exclusifs dorés</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">📊</span>
                <span class="feature-text">Stats avancées + graphiques</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">🎯</span>
                <span class="feature-text">Défis personnalisés</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">🔔</span>
                <span class="feature-text">Notifications push</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">🚫</span>
                <span class="feature-text"><strong>SANS publicité</strong></span>
            </div>
        </div>
        
        <div class="pricing">
            <div class="price-tag">2,99€</div>
            <div class="price-period">par mois • sans engagement</div>
        </div>
        
        <button class="cta-button" onclick="window.location.href='/checkout_premium'">
            🚀 Passer Premium Maintenant
        </button>
        
        <div class="guarantee">
            ✓ Satisfait ou remboursé 30 jours<br>
            ✓ Annulation en 1 clic
        </div>
    </div>
</body>
</html>
```

**Taux de conversion attendu :** 3-7%

---

## 📊 TABLEAU DE BORD REVENUS

```python
# revenue_dashboard.py

def calculate_monthly_revenue(active_users):
    """Calcule le revenu mensuel projeté"""
    
    # Hypothèses
    affiliate_click_rate = 0.10  # 10% cliquent
    affiliate_conversion = 0.04   # 4% achètent
    avg_commission = 1.20         # 1,20€ par vente
    
    sponsor_campaigns = 2         # 2 campagnes/mois
    sponsor_price = 350           # 350€ par campagne
    
    premium_conversion = 0.05     # 5% passent premium
    premium_price = 2.99          # 2,99€/mois
    
    # Calculs
    affiliate_revenue = (
        active_users * 
        affiliate_click_rate * 
        affiliate_conversion * 
        avg_commission
    )
    
    sponsor_revenue = sponsor_campaigns * sponsor_price
    
    premium_revenue = active_users * premium_conversion * premium_price
    
    total = affiliate_revenue + sponsor_revenue + premium_revenue
    
    return {
        'affiliate': round(affiliate_revenue, 2),
        'sponsors': sponsor_revenue,
        'premium': round(premium_revenue, 2),
        'total': round(total, 2)
    }


# Projections
print("PROJECTIONS REVENUS MENSUELS")
print("=" * 50)

for users in [100, 500, 1000, 5000]:
    revenue = calculate_monthly_revenue(users)
    print(f"\n{users} utilisateurs actifs:")
    print(f"  Affiliation : {revenue['affiliate']}€")
    print(f"  Sponsors    : {revenue['sponsors']}€")
    print(f"  Premium     : {revenue['premium']}€")
    print(f"  TOTAL       : {revenue['total']}€")
    print(f"  Annuel      : {revenue['total'] * 12}€")
```

**Résultats :**
```
100 utilisateurs  →    87€/mois   →  1,044€/an
500 utilisateurs  →   423€/mois   →  5,076€/an
1000 utilisateurs →   846€/mois   → 10,152€/an
5000 utilisateurs → 4,207€/mois   → 50,484€/an
```

---

## 🎯 RÈGLES D'OR

### ✅ À FAIRE
1. **Contextualiser** : Pub pertinente au moment opportun
2. **Ajouter de la valeur** : Vraies recommandations utiles
3. **Être transparent** : "Lien affilié" visible
4. **Récompenser** : Points bonus si achat
5. **Mesurer** : Tracker tous les clics/conversions

### ❌ À ÉVITER
1. Pop-ups intrusifs
2. Vidéos auto-play
3. Publicités non pertinentes
4. Trop de pubs (max 1-2 par page)
5. Ralentir l'app avec des scripts lourds

---

## 🚀 IMPLÉMENTATION RAPIDE

### Jour 1 : Affiliation Amazon (4h)
- Créer compte Amazon Associates
- Intégrer liens dans `task_page.html`
- Tracker les clics
- Tester le parcours

### Jour 2 : Système de tracking (2h)
- Table `affiliate_clicks`
- Dashboard analytics
- Calcul des conversions

### Jour 3 : Sponsoring (3h)
- Créer système de campagnes
- Design badges sponsorisés
- Contact premières marques

### Jour 4 : Premium (4h)
- Page upgrade attractive
- Intégration Stripe/PayPal
- Logique d'abonnement

---

## 💰 OBJECTIF 6 MOIS

```
Utilisateurs : 1000 actifs
Revenus mensuels :
  - Affiliation : 120€
  - Sponsors : 700€ (2 campagnes)
  - Premium : 150€ (50 abonnés)
  ─────────────────────
  TOTAL : 970€/mois
  
Annuel : 11,640€
```

---

**🎯 La monétisation intelligente = Revenus + Expérience préservée !**

*Prêt à monétiser ? Let's make money! 💰*
