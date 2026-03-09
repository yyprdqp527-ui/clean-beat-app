#!/bin/bash
# Script de test rapide pour vérifier la synchronisation des points

echo "🔄 REDÉMARRAGE DU SERVEUR..."
pkill -9 -f 'python3 app.py' 2>/dev/null
sleep 1

echo "🚀 LANCEMENT DU SERVEUR..."
python3 app.py &
SERVER_PID=$!
sleep 3

echo ""
echo "✅ Serveur démarré (PID: $SERVER_PID)"
echo ""
echo "📋 INSTRUCTIONS DE TEST:"
echo ""
echo "1. Ouvrez 2 navigateurs (ou 2 onglets incognito)"
echo "2. Connectez-vous avec 2 joueurs différents de la même maison"
echo "3. Ouvrez la console (F12) dans les 2 navigateurs"
echo "4. Sur le premier navigateur, validez une tâche"
echo "5. Observez le second navigateur : les points doivent s'actualiser IMMÉDIATEMENT"
echo ""
echo "🔍 Dans la console, vous devriez voir:"
echo "   🔌 WebSocket: Connecté au serveur"
echo "   🏠 WebSocket: Rejoint la room house_XXX"
echo "   📊 WebSocket: Mise à jour des points reçue"
echo ""
echo "💡 Astuce: Gardez les consoles ouvertes pour voir les événements en temps réel"
echo ""
echo "Pour arrêter le serveur: pkill -9 -f 'python3 app.py'"
echo ""
