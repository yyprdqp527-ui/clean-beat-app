#!/usr/bin/env python3
"""Test pour comprendre pourquoi Lucien n'a pas de message baby_tracking"""

# Test des conditions de détection baby tracking

# 1. Test de détection de tâche bébé
task_name = "Donner le biberon"
print(f"Task name: '{task_name}'")
print(f"Contient 'biberon': {'biberon' in task_name.lower()}")

is_baby_task = task_name and ('biberon' in task_name.lower() or 'couche' in task_name.lower() or 'dormir' in task_name.lower())
print(f"is_baby_task: {is_baby_task}")

# 2. Test détection type
if 'biberon' in task_name.lower():
    task_type_baby = 'biberon'
elif 'couche' in task_name.lower():
    task_type_baby = 'couches'  
elif 'dormir' in task_name.lower():
    task_type_baby = 'sommeil'
else:
    task_type_baby = None

print(f"task_type_baby: {task_type_baby}")

# 3. Simulation avec tracking_time
tracking_time = "07:44"
print(f"tracking_time: {tracking_time}")
print(f"Condition baby tracking: {tracking_time and is_baby_task}")

# Le message qui devrait être créé
if tracking_time and is_baby_task:
    player_name = "Lucien"
    bottle_ml = "120"
    observations = "Bébé content"
    
    if task_type_baby == 'biberon':
        ml_text = f" ({bottle_ml} ml)" if bottle_ml else ""
        message_text = f"🍼 {player_name} a donné le biberon à {tracking_time}{ml_text}"
        if observations:
            message_text += f"\n📝 {observations}"
    
    print(f"Message à créer: {message_text}")
else:
    print("❌ Aucun message ne serait créé")