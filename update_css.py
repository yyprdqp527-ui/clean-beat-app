import re

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Le nouveau CSS à insérer
new_css = '''        /* Animation pulsation gagnant */
        @keyframes winnerPulse {
            0%, 100% { 
                transform: scale(1); 
                box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.7);
            }
            50% { 
                transform: scale(1.1); 
                box-shadow: 0 0 20px 10px rgba(255, 215, 0, 0.5);
            }
        }
        
        @keyframes pointsPulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.2); }
            100% { transform: scale(1); }
        }
        
        .avatar-celebrating {
            animation: winnerPulse 0.8s ease-in-out 3;
            border: 3px solid #FFD700 !important;
            z-index: 9999 !important;
        }
        
        .avatar-halo {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 150%;
            height: 150%;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255,215,0,0.6) 0%, rgba(253,174,84,0.3) 40%, transparent 70%);
            transform: translate(-50%, -50%);
            pointer-events: none;
            z-index: -1;
            animation: avatar-halo-pulse 1.5s ease-in-out infinite;
        }
        
        .points-popup {
            position: absolute;
            top: -40px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #FFD700, #FFA500);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 16px;
            white-space: nowrap;
            animation: popupFloat 4s ease-out forwards;
            z-index: 10000;
            box-shadow: 0 4px 15px rgba(255, 165, 0, 0.5);
            pointer-events: none;
        }
        
        @keyframes popupFloat {
            0% { opacity: 0; transform: translateX(-50%) translateY(20px); }
            20% { opacity: 1; transform: translateX(-50%) translateY(0); }
            80% { opacity: 1; }
            100% { opacity: 0; transform: translateX(-50%) translateY(-30px); }
        }
        
        .winner-star {'''

# Pattern pour trouver l'ancien bloc CSS
old_pattern = r'/\* Animation de victoire améliorée \*/\s*@keyframes winnerPulse \{[^}]+\}\s*@keyframes pointsPulse \{[^}]+\}\s*\.avatar-celebrating \{[^}]+\}\s*\.avatar-halo \{[^}]+\}\s*\.points-popup \{[^}]+\}\s*\.winner-star \{'

# Remplacer toutes les occurrences
content_new = re.sub(old_pattern, new_css, content)

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content_new)

print("✅ CSS mis à jour avec succès!")
