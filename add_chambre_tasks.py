import sqlite3

# Connexion à la base de données
conn = sqlite3.connect('cleanbeat.db')
cursor = conn.cursor()

# Tâches à ajouter pour la catégorie "chambre"
tasks = [
    ("Aérer sa chambre", "chambre", "chambre ados/aerer sa chambre.webp"),
    ("Faire ses devoirs", "chambre", "chambre ados/faire ses devoir.webp"),
    ("Faire son lit", "chambre", "chambre ados/faire son lit.webp"),
    ("Mettre ses vêtements dans la corbeille", "chambre", "chambre ados/mettre ses vetements dans la corbeille.webp"),
    ("Ranger sa chambre", "chambre", "chambre ados/ranger sa chambre.webp"),
    ("Vider sa corbeille", "chambre", "chambre ados/vider sa corbeille.webp")
]

# Insertion des tâches
for task_name, category, image_path in tasks:
    try:
        cursor.execute("""
            INSERT INTO tasks (name, category, image_path, points)
            VALUES (?, ?, ?, 10)
        """, (task_name, category, image_path))
        print(f"✅ Tâche ajoutée : {task_name}")
    except sqlite3.IntegrityError:
        print(f"⚠️  Tâche déjà existante : {task_name}")

# Validation et fermeture
conn.commit()
conn.close()

print("\n🎉 Toutes les tâches ont été ajoutées à la catégorie Chambre !")
