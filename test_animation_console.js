// ============================================================================
// SCRIPT DE TEST ANIMATION ÉTOILES - À exécuter dans la console du navigateur
// ============================================================================

console.log('🎬 === TEST ANIMATION ÉTOILES DIRECTEMENT ===');

// 1. Vérifier que la fonction existe
if (typeof window.triggerCelebrationAnimation === 'function') {
    console.log('✅ Fonction triggerCelebrationAnimation trouvée');
} else {
    console.log('❌ Fonction triggerCelebrationAnimation NON trouvée');
    console.log('Fonctions disponibles sur window:');
    Object.keys(window).filter(k => k.includes('trigger') || k.includes('celebration') || k.includes('animation')).forEach(k => console.log('  -', k));
}

// 2. Lister tous les avatars disponibles
console.log('\n👤 === AVATARS DISPONIBLES ===');
const avatars = document.querySelectorAll('.avatar-square-wrapper[data-player-email]');
console.log(`Trouvé ${avatars.length} avatar(s):`);
avatars.forEach((avatar, i) => {
    const email = avatar.getAttribute('data-player-email');
    const title = avatar.getAttribute('title');
    console.log(`  ${i+1}. Email: "${email}", Titre: "${title}"`);
});

if (avatars.length === 0) {
    console.log('❌ Aucun avatar trouvé avec data-player-email');
    // Chercher d'autres types d'avatars
    const allAvatars = document.querySelectorAll('.avatar-square, .avatar-square-wrapper');
    console.log(`Autres éléments d'avatar trouvés: ${allAvatars.length}`);
    allAvatars.forEach((el, i) => {
        console.log(`  ${i+1}. ${el.className}, id: ${el.id}`);
    });
}

// 3. Test direct de l'animation sur le premier avatar
if (avatars.length > 0 && typeof window.triggerCelebrationAnimation === 'function') {
    console.log('\n🎯 === TEST ANIMATION ===');
    const firstAvatar = avatars[0];
    const testEmail = firstAvatar.getAttribute('data-player-email');
    const testName = firstAvatar.getAttribute('title') || 'Test';
    
    console.log(`Test avec: ${testName} (${testEmail})`);
    
    try {
        window.triggerCelebrationAnimation(50, testEmail, testName, '🎯 Test Console Direct');
        console.log('✅ Animation déclenchée !');
    } catch (e) {
        console.log('❌ Erreur animation:', e);
    }
}

// 4. Test de l'événement WebSocket (simulation)
console.log('\n📡 === TEST WEBSOCKET ===');
if (typeof io !== 'undefined' && window.socket) {
    console.log('✅ Socket.IO disponible');
    console.log('État socket:', window.socket.connected ? 'CONNECTÉ' : 'DÉCONNECTÉ');
    
    if (avatars.length > 0) {
        const testEmail = avatars[0].getAttribute('data-player-email');
        const testName = avatars[0].getAttribute('title') || 'Test';
        
        // Simuler réception événement task_celebration
        const fakeData = {
            player_email: testEmail,
            player_name: testName,
            points: 35,
            task_name: '🎯 Test WebSocket Simulé'
        };
        
        console.log('📤 Simulation événement task_celebration avec:', fakeData);
        
        // Déclencher manuellement l'handler
        if (window.socket && window.socket._callbacks && window.socket._callbacks['$task_celebration']) {
            console.log('✅ Handler task_celebration trouvé, déclenchement...');
            try {
                window.socket._callbacks['$task_celebration'][0](fakeData);
                console.log('✅ Handler exécuté !');
            } catch (e) {
                console.log('❌ Erreur handler:', e);
            }
        } else {
            console.log('❌ Handler task_celebration non trouvé');
        }
    }
} else {
    console.log('❌ Socket.IO non disponible');
    console.log('window.socket:', typeof window.socket);
    console.log('io:', typeof io);
}

// 5. Vérifications CSS
console.log('\n🎨 === VÉRIFICATIONS CSS ===');
const styles = ['avatar-celebrating', 'avatar-halo', 'points-popup', 'winner-star'];
styles.forEach(className => {
    const rules = Array.from(document.styleSheets).flatMap(sheet => {
        try {
            return Array.from(sheet.cssRules || []);
        } catch (e) {
            return [];
        }
    }).filter(rule => rule.selectorText && rule.selectorText.includes(className));
    
    if (rules.length > 0) {
        console.log(`✅ Styles ${className}: ${rules.length} règle(s) trouvée(s)`);
    } else {
        console.log(`❌ Styles ${className}: aucune règle trouvée`);
    }
});

console.log('\n🎬 === FIN TEST ===');