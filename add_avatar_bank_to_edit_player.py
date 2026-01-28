#!/usr/bin/env python3
"""
Script pour ajouter la banque d'avatars à edit_player.html
"""

file_path = "/Users/anne-gaelledaval/Downloads/Appli web-2/templates/edit_player.html"

# Lire le contenu actuel
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Vérifier si la banque est déjà ajoutée
if 'avatar-bank' in content:
    print("✓ La banque d'avatars est déjà présente dans le fichier!")
    exit(0)

print("⚠️  La banque d'avatars n'est PAS présente. Ajout en cours...")

# 1. Ajouter les styles CSS pour la banque d'avatars
css_insertion = """    .photo-btn:active {
        transform: translateY(0);
    }
    
    /* Banque d'avatars */
    .avatar-bank {
        margin-bottom: 28px;
    }
    
    .avatar-bank-title {
        font-size: 15px;
        font-weight: 700;
        color: var(--dark);
        margin-bottom: 12px;
        text-align: center;
    }
    
    .avatar-categories {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }
    
    .category-btn {
        padding: 8px 16px;
        border: 2px solid rgba(166, 211, 220, 0.4);
        border-radius: 20px;
        background: white;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        font-family: 'Montserrat', sans-serif;
        color: var(--dark);
    }
    
    .category-btn:hover {
        border-color: var(--teal-light);
        background: rgba(166, 211, 220, 0.15);
    }
    
    .category-btn.active {
        background: linear-gradient(135deg, var(--gold) 0%, var(--peach) 100%);
        border-color: var(--gold);
        color: white;
    }
    
    .avatars-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    
    .avatar-item {
        aspect-ratio: 1;
        border-radius: 12px;
        border: 3px solid transparent;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        background-size: cover;
        background-position: center;
    }
    
    .avatar-item:hover {
        border-color: var(--teal-light);
        transform: scale(1.08);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .avatar-item.selected {
        border-color: var(--gold);
        box-shadow: 0 0 0 3px rgba(253, 174, 84, 0.3), 0 4px 15px rgba(253, 174, 84, 0.35);
        transform: scale(1.05);
    }
    
    /* Formulaire */"""

content = content.replace(
    """    .photo-btn:active {
        transform: translateY(0);
    }
    
    /* Formulaire */""",
    css_insertion
)

# 2. Ajouter les styles responsive
content = content.replace(
    """        .photo-btn {
            padding: 10px 14px;
            font-size: 13px;
        }
        
        .form-input {""",
    """        .photo-btn {
            padding: 10px 14px;
            font-size: 13px;
        }
        
        .avatars-grid {
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }
        
        .form-input {"""
)

content = content.replace(
    """        .photo-btn {
            width: 100%;
            justify-content: center;
        }
    }
</style>""",
    """        .photo-btn {
            width: 100%;
            justify-content: center;
        }
        
        .avatars-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }
    }
</style>"""
)

# 3. Ajouter le HTML de la banque d'avatars
html_insertion = """                <input type="file" id="fileInput" accept="image/*" class="hidden" onchange="handlePhotoCapture(event)">
                <input type="hidden" id="selectedPhoto" name="photo_data">
                <input type="hidden" id="selectedAvatar" name="avatar" value="">
            </div>

            <!-- Banque d'avatars -->
            <div class="avatar-bank">
                <div class="avatar-bank-title">🎭 Ou choisir un avatar</div>
                
                <div class="avatar-categories">
                    <button type="button" class="category-btn active" onclick="showCategory('boys')">👦 Garçons</button>
                    <button type="button" class="category-btn" onclick="showCategory('girls')">👧 Filles</button>
                </div>
                
                <div class="avatars-grid" id="avatars-grid"></div>
            </div>

            <div class="form-group">"""

content = content.replace(
    """                <input type="file" id="fileInput" accept="image/*" class="hidden" onchange="handlePhotoCapture(event)">
                <input type="hidden" id="selectedPhoto" name="photo_data">
            </div>

            <div class="form-group">""",
    html_insertion
)

# 4. Remplacer le JavaScript
js_new = """<script>
    const avatars = {
        boys: [
            'avatar_boy_1.svg', 'avatar_boy_2.svg', 'avatar_boy_3.svg', 'avatar_boy_4.svg', 'avatar_boy_5.svg',
            'avatar_boy_6.svg', 'avatar_boy_7.svg', 'avatar_boy_8.svg', 'avatar_boy_9.svg', 'avatar_boy_10.svg',
            'avatar_boy_11.svg', 'avatar_boy_12.svg', 'avatar_boy_13.svg', 'avatar_boy_14.svg', 'avatar_boy_15.svg'
        ],
        girls: [
            'avatar_girl_1.svg', 'avatar_girl_2.svg', 'avatar_girl_3.svg', 'avatar_girl_4.svg', 'avatar_girl_5.svg',
            'avatar_girl_6.svg', 'avatar_girl_7.svg', 'avatar_girl_8.svg', 'avatar_girl_9.svg', 'avatar_girl_10.svg',
            'avatar_girl_11.svg', 'avatar_girl_12.svg', 'avatar_girl_13.svg', 'avatar_girl_14.svg'
        ]
    };
    
    let currentCategory = 'boys';
    let selectedAvatarFile = null;
    
    function showCategory(category) {
        currentCategory = category;
        
        // Update buttons
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        
        // Display avatars
        const grid = document.getElementById('avatars-grid');
        grid.innerHTML = '';
        
        avatars[category].forEach(file => {
            const div = document.createElement('div');
            div.className = 'avatar-item';
            div.style.backgroundImage = `url('/static/avatars/${file}')`;
            div.onclick = () => selectAvatar(file, div);
            grid.appendChild(div);
        });
    }
    
    function selectAvatar(file, element) {
        // Remove previous selection
        document.querySelectorAll('.avatar-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Select new avatar
        element.classList.add('selected');
        selectedAvatarFile = file;
        
        // Update preview
        const preview = document.getElementById('photoPreview');
        preview.innerHTML = `<img src="/static/avatars/${file}" alt="Avatar" id="preview-img">`;
        
        // Update form
        document.getElementById('selectedAvatar').value = file;
        document.getElementById('selectedPhoto').value = '';
        
        // Clear file input
        document.getElementById('fileInput').value = '';
    }
    
    function handlePhotoCapture(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const preview = document.getElementById('photoPreview');
                preview.innerHTML = `<img src="${e.target.result}" alt="Aperçu" id="preview-img">`;
                document.getElementById('selectedPhoto').value = e.target.result;
                
                // Deselect avatar
                document.querySelectorAll('.avatar-item').forEach(item => {
                    item.classList.remove('selected');
                });
                selectedAvatarFile = null;
                document.getElementById('selectedAvatar').value = '';
            };
            reader.readAsDataURL(file);
        }
    }
    
    // Load boys category by default
    window.addEventListener('DOMContentLoaded', () => {
        showCategory('boys');
    });
    
    document.getElementById('edit-form').addEventListener('submit', async function(e) {"""

js_old = """<script>
    function handlePhotoCapture(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const preview = document.getElementById('photoPreview');
                preview.innerHTML = `<img src="${e.target.result}" alt="Aperçu" id="preview-img">`;
                document.getElementById('selectedPhoto').value = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    }
    
    document.getElementById('edit-form').addEventListener('submit', async function(e) {"""

content = content.replace(js_old, js_new)

# Sauvegarder
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Banque d'avatars ajoutée avec succès!")
print(f"   Fichier modifié: {file_path}")
print(f"   Nouvelles lignes: {len(content.splitlines())}")
print("\n🔄 Actualisez votre navigateur (Cmd+Shift+R ou Ctrl+F5)")
