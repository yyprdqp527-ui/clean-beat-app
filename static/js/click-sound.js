/**
 * 🔊 CleanBeat - Sons de l'application
 * Son de clic type iPhone + Son festif pour les points
 */

(function() {
    'use strict';
    
    // Context audio partagé
    let audioCtx = null;
    let audioUnlocked = false;
    
    // Initialiser et débloquer le contexte audio
    function getAudioContext() {
        if (!audioCtx) {
            try {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            } catch(e) {
                console.log('Audio non supporté');
                return null;
            }
        }
        return audioCtx;
    }
    
    // Débloquer l'audio (nécessaire sur mobile/navigateurs modernes)
    function unlockAudio() {
        if (audioUnlocked) return;
        
        const ctx = getAudioContext();
        if (!ctx) return;
        
        // Reprendre si suspendu
        if (ctx.state === 'suspended') {
            ctx.resume().then(() => {
                audioUnlocked = true;
                console.log('🔊 Audio débloqué !');
            });
        } else {
            audioUnlocked = true;
        }
        
        // Jouer un son silencieux pour débloquer
        try {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            gain.gain.value = 0.001; // Quasi-silencieux
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.01);
        } catch(e) {}
    }
    
    // 🔊 Son de clic type iPhone
    function playClickSound() {
        const ctx = getAudioContext();
        if (!ctx) return;
        
        // S'assurer que l'audio est débloqué
        if (ctx.state === 'suspended') {
            ctx.resume();
        }
        
        try {
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            const gainNode = ctx.createGain();
            
            osc.connect(gainNode);
            gainNode.connect(ctx.destination);
            
            // Son type iPhone - tick court et net
            osc.type = 'sine';
            osc.frequency.setValueAtTime(1400, now);
            osc.frequency.exponentialRampToValueAtTime(1000, now + 0.02);
            
            // Volume plus fort pour être audible
            gainNode.gain.setValueAtTime(0.3, now);
            gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
            
            osc.start(now);
            osc.stop(now + 0.05);
        } catch(e) {
            console.log('Erreur son clic:', e);
        }
    }
    
    // 🎉 Son SUPER festif pour les points gagnés - célébration avec fanfare !
    function playVictorySound() {
        const ctx = getAudioContext();
        if (!ctx) return;
        
        if (ctx.state === 'suspended') {
            ctx.resume();
        }
        
        try {
            const now = ctx.currentTime;
            
            // === FANFARE INITIALE ===
            const fanfare = [523, 659, 784, 1047];
            fanfare.forEach((freq, i) => {
                const osc = ctx.createOscillator();
                const gainNode = ctx.createGain();
                osc.connect(gainNode);
                gainNode.connect(ctx.destination);
                osc.type = 'square'; // Son plus brillant
                const startTime = now + i * 0.12;
                osc.frequency.setValueAtTime(freq, startTime);
                gainNode.gain.setValueAtTime(0.3, startTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + 0.15);
                osc.start(startTime);
                osc.stop(startTime + 0.15);
            });
            
            // === ACCORD DE VICTOIRE ===
            const chordTime = now + 0.55;
            const chordNotes = [523, 659, 784]; // Do-Mi-Sol
            chordNotes.forEach(freq => {
                const osc = ctx.createOscillator();
                const gainNode = ctx.createGain();
                osc.connect(gainNode);
                gainNode.connect(ctx.destination);
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, chordTime);
                gainNode.gain.setValueAtTime(0.25, chordTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, chordTime + 0.5);
                osc.start(chordTime);
                osc.stop(chordTime + 0.5);
            });
            
            // === DING BRILLANT FINAL ===
            const dingTime = now + 0.7;
            const ding = ctx.createOscillator();
            const dingGain = ctx.createGain();
            ding.connect(dingGain);
            dingGain.connect(ctx.destination);
            ding.type = 'triangle';
            ding.frequency.setValueAtTime(1568, dingTime); // Sol aigu
            dingGain.gain.setValueAtTime(0.35, dingTime);
            dingGain.gain.exponentialRampToValueAtTime(0.01, dingTime + 0.6);
            ding.start(dingTime);
            ding.stop(dingTime + 0.6);
            
            // === PÉTILLEMENTS FESTIFS ===
            for (let p = 0; p < 5; p++) {
                const sparkle = ctx.createOscillator();
                const sparkleGain = ctx.createGain();
                sparkle.connect(sparkleGain);
                sparkleGain.connect(ctx.destination);
                sparkle.type = 'sine';
                const sparkleFreq = 1800 + Math.random() * 1200;
                sparkle.frequency.setValueAtTime(sparkleFreq, now);
                const sparkleTime = now + 0.9 + Math.random() * 0.4;
                sparkleGain.gain.setValueAtTime(0.15, sparkleTime);
                sparkleGain.gain.exponentialRampToValueAtTime(0.01, sparkleTime + 0.1);
                sparkle.start(sparkleTime);
                sparkle.stop(sparkleTime + 0.1);
            }
            
            console.log('🎉 Son festif victoire joué !');
            
        } catch(e) {
            console.log('Erreur son victoire:', e);
        }
    }
    
    // Exposer globalement
    window.playClickSound = playClickSound;
    window.playSound = playClickSound;
    window.playSuccessSound = playClickSound;
    window.playNavSound = playClickSound;
    window.playRoomClickSound = playClickSound;
    window.playProgressSound = playVictorySound;
    window.playTaskCreatedSound = playClickSound;
    window.playVictorySound = playVictorySound;
    window.unlockAudio = unlockAudio;
    
    // Sélecteurs pour éléments cliquables
    const CLICKABLE_SELECTORS = [
        'button',
        'a.btn',
        '.btn',
        'input[type="submit"]',
        'input[type="button"]',
        '.task-btn',
        '.nav-btn',
        '.action-btn',
        '.clickable',
        '[role="button"]',
        '.burger-menu',
        '.burger-nav-item',
        '.burger-close',
        '.dashboard-toggle',
        '.avatar-square',
        '.avatar-col',
        '.room-group',
        '[data-room]',
        'svg a',
        '.player-option',
        '.gift-card',
        '.reward-btn',
        '.menu-item',
        '.card-clickable',
        '.task-card',
        '.custom-task',
        '.points-badge',
        '.points-edit-trigger',
        '.add-task-btn',
        '.back-btn-glass',
        '.room-header',
        '.category-card',
        '.category-btn',
        'a[href*="task"]',
        'a[href*="menu"]'
    ].join(', ');
    
    // Appliquer le son au clic
    document.addEventListener('click', function(e) {
        // Débloquer l'audio au premier clic
        unlockAudio();
        
        const clickedElement = e.target.closest(CLICKABLE_SELECTORS);
        if (clickedElement) {
            playClickSound();
        }
    }, true);
    
    // Débloquer l'audio dès la première interaction
    document.addEventListener('touchstart', unlockAudio, { once: true });
    document.addEventListener('mousedown', unlockAudio, { once: true });
    document.addEventListener('keydown', unlockAudio, { once: true });
    
    console.log('🔊 CleanBeat Sounds chargé');
})();
