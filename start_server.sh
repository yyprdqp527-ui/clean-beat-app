#!/bin/bash

# Script de démarrage robuste pour CleanBeat
# Ce script démarre le serveur Flask avec une meilleure gestion des erreurs

echo "🚀 Démarrage de CleanBeat..."

# Arrêter tout processus existant sur le port 8000
echo "🔍 Vérification des processus existants..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Processus précédent arrêté"
fi

# Attendre que le port soit libéré
sleep 2

# Changer vers le répertoire de l'application
cd "$(dirname "$0")"

# Créer un répertoire pour les logs si nécessaire
mkdir -p logs

# Démarrer le serveur Flask avec redirection des logs
echo "🎯 Lancement du serveur sur le port 8000..."
echo "📝 Les logs sont disponibles dans logs/cleanbeat.log"
echo ""

# Lancer le serveur avec gestion des erreurs
python3 app.py 2>&1 | tee logs/cleanbeat.log

# Si le serveur s'arrête, afficher un message
echo ""
echo "⚠️  Le serveur s'est arrêté"
echo "📝 Consultez logs/cleanbeat.log pour plus de détails"
