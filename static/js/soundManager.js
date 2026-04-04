/**
 * SoundManager — Système audio centralisé CleanBeat
 * Howler.js (sons fichier) + Web Audio API (synthèse UI)
 *
 * API publique :
 *   SoundManager.play('eventName')
 *   SoundManager.setAmbient('silence' | 'lofi' | 'epic')
 *   SoundManager.setVolume('master' | 'ui' | 'game' | 'ambient', 0‑1)
 *   SoundManager.toggle([bool])
 *   SoundManager.getPrefs()
 *   SoundManager.openPanel() / SoundManager.closePanel()
 */
(function () {
    'use strict';

    // ─── Constantes ────────────────────────────────────────────
    var STORAGE_KEY = 'cleanbeat_sound_prefs';
    var CROSSFADE   = 2.5;           // secondes de crossfade ambiant
    var DEFAULT_PREFS = {
        enabled       : true,
        masterVolume  : 0.7,
        uiVolume      : 0.8,
        gameVolume    : 0.8,
        ambientVolume : 0.3,
        currentAmbient: 'silence'
    };

    // ─── État interne ──────────────────────────────────────────
    var prefs           = loadPrefs();
    var audioCtx        = null;
    var isUnlocked      = false;
    var howlSounds      = {};
    var ambientState    = { nodes: null, name: 'silence' };
    var panelInjected   = false;

    // ─── AudioContext ──────────────────────────────────────────
    function getCtx() {
        if (!audioCtx) {
            try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
            catch (e) { return null; }
        }
        if (audioCtx.state === 'suspended') audioCtx.resume();
        return audioCtx;
    }

    function unlock() {
        if (isUnlocked) return;
        var ctx = getCtx();
        if (ctx && ctx.state === 'suspended') {
            ctx.resume().then(function () { isUnlocked = true; });
        } else {
            isUnlocked = true;
        }
    }

    // ─── Préférences (localStorage) ────────────────────────────
    function loadPrefs() {
        // Purger l'ancien état potentiellement corrompu (volumes à 0, enabled false)
        try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
        // Toujours utiliser les réglages par défaut
        var out = {};
        for (var k in DEFAULT_PREFS) out[k] = DEFAULT_PREFS[k];
        return out;
    }

    function savePrefs() {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch (e) { /* ignore */ }
        syncPanel();
    }

    // ─── Volumes effectifs ─────────────────────────────────────
    function vol(category) {
        if (!prefs.enabled) return 0;
        var catVol = category === 'ui'      ? prefs.uiVolume
                   : category === 'game'    ? prefs.gameVolume
                   : category === 'ambient' ? prefs.ambientVolume
                   : 1;
        return prefs.masterVolume * catVol;
    }

    // ─── Howler.js – sons fichier ──────────────────────────────
    function initHowlSounds() {
        if (typeof Howl === 'undefined') {
            console.warn('SoundManager: Howler.js non chargé, sons fichier désactivés');
            return;
        }
        howlSounds.gainPoints = new Howl({
            src: ['/static/audio/notification-sound-3-262896.mp3'],
            volume: 0.8, preload: true
        });
        howlSounds.receiveMessage = new Howl({
            src: ['/static/audio/livechat-129007.mp3'],
            volume: 0.7, preload: true
        });
        howlSounds.sendMessage = new Howl({
            src: ['/static/audio/notification-smooth-modern-stereo-332449.mp3'],
            volume: 0.5, preload: true
        });
    }

    // ─── Sons synthétisés (Web Audio) ──────────────────────────
    var synth = {

        /* Clic bouton — court/net (100 ms) */
        buttonClick: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('ui'); if (!v) return;
            var osc  = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(800, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(400, ctx.currentTime + 0.08);
            gain.gain.setValueAtTime(0.35 * v, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.1);
        },

        /* Sélection pièce — ding bref (150 ms) */
        selectRoom: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('ui'); if (!v) return;
            var osc  = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(523, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(784, ctx.currentTime + 0.12);
            gain.gain.setValueAtTime(0.30 * v, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.15);
        },

        /* Pièce plein écran — cinématique (600 ms) */
        roomFullscreen: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('ui'); if (!v) return;
            var osc  = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(523, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(784, ctx.currentTime + 0.6);
            gain.gain.setValueAtTime(0, ctx.currentTime);
            gain.gain.linearRampToValueAtTime(0.08 * v, ctx.currentTime + 0.15);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.65);
        },

        /* Perte de points — descendant discret (250 ms) */
        losePoints: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('game'); if (!v) return;
            var osc  = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(600, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 0.25);
            gain.gain.setValueAtTime(0.12 * v, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.3);
        },

        /* Victoire — accord ascendant C5‑E5‑G5‑C6 (600 ms) */
        victory: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('game'); if (!v) return;
            [523, 659, 784, 1047].forEach(function (f, i) {
                var osc  = ctx.createOscillator();
                var gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'sine';
                osc.frequency.value = f;
                var t = ctx.currentTime + i * 0.12;
                gain.gain.setValueAtTime(0.3 * v, t);
                gain.gain.exponentialRampToValueAtTime(0.001, t + 0.2);
                osc.start(t);
                osc.stop(t + 0.25);
            });
        },

        /* Succès court — ding confirmation (100 ms) */
        success: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('ui'); if (!v) return;
            var osc  = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(1200, ctx.currentTime);
            gain.gain.setValueAtTime(0.3 * v, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.12);
        },

        /* Navigation — whoosh léger (80 ms) */
        navigate: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('ui'); if (!v) return;
            var osc  = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(300, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(600, ctx.currentTime + 0.08);
            gain.gain.setValueAtTime(0.1 * v, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.1);
        },

        /* Entourloupe émise — suspense montant (350 ms) */
        suspicionEmit: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('game'); if (!v) return;
            [330, 392, 466].forEach(function (f, i) {
                var osc = ctx.createOscillator();
                var gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'sawtooth';
                var t = ctx.currentTime + i * 0.1;
                osc.frequency.setValueAtTime(f, t);
                gain.gain.setValueAtTime(0.08 * v, t);
                gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
                osc.start(t);
                osc.stop(t + 0.15);
            });
        },

        /* Malus envoyé — impact sourd descendant (400 ms) */
        malusImpact: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('game'); if (!v) return;
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(400, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(80, ctx.currentTime + 0.35);
            gain.gain.setValueAtTime(0.15 * v, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.45);
        },

        /* Bonus envoyé — ding joyeux ascendant (300 ms) */
        bonusDing: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('game'); if (!v) return;
            [523, 659, 784].forEach(function (f, i) {
                var osc = ctx.createOscillator();
                var gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'sine';
                var t = ctx.currentTime + i * 0.08;
                osc.frequency.setValueAtTime(f, t);
                gain.gain.setValueAtTime(0.12 * v, t);
                gain.gain.exponentialRampToValueAtTime(0.001, t + 0.15);
                osc.start(t);
                osc.stop(t + 0.18);
            });
        },

        /* Spin roue — tick-tick accéléré (600 ms) */
        wheelSpin: function () {
            var ctx = getCtx(); if (!ctx) return;
            var v = vol('game'); if (!v) return;
            for (var i = 0; i < 8; i++) {
                var osc = ctx.createOscillator();
                var gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'sine';
                var t = ctx.currentTime + i * (0.06 + i * 0.005);
                osc.frequency.setValueAtTime(800 + i * 50, t);
                gain.gain.setValueAtTime(0.06 * v, t);
                gain.gain.exponentialRampToValueAtTime(0.001, t + 0.04);
                osc.start(t);
                osc.stop(t + 0.05);
            }
        }
    };

    // ─── Catégorie par événement (pour Howler volume) ──────────
    var eventCategory = {
        gainPoints     : 'game',
        losePoints     : 'game',
        victory        : 'game',
        suspicionEmit  : 'game',
        malusImpact    : 'game',
        bonusDing      : 'game',
        wheelSpin      : 'game',
        receiveMessage : 'ui',
        sendMessage    : 'ui',
        buttonClick    : 'ui',
        selectRoom     : 'ui',
        roomFullscreen : 'ui',
        success        : 'ui',
        navigate       : 'ui'
    };

    // ─── play() — point d'entrée unique ────────────────────────
    function play(eventName) {
        if (!prefs.enabled) return;

        // Sons fichier Howler
        if (howlSounds[eventName]) {
            var h = howlSounds[eventName];
            var cat = eventCategory[eventName] || 'ui';
            h.volume(vol(cat));
            h.play();
            return;
        }

        // Sons synthétisés — résumer + jouer immédiatement (pas de .then()
        // car iOS Safari considère les microtasks hors geste utilisateur)
        if (synth[eventName]) {
            var ctx = getCtx();
            if (!ctx) return;
            if (ctx.state !== 'running') ctx.resume();
            try { synth[eventName](); } catch (e) { console.error('SoundManager synth error:', eventName, e); }
            return;
        }

        console.warn('SoundManager: événement inconnu "' + eventName + '"');
    }

    // ─── Ambient generatif ─────────────────────────────────────

    function stopAmbient(fadeTime) {
        var nodes = ambientState.nodes;
        if (!nodes) return;
        fadeTime = fadeTime || CROSSFADE;
        var ctx = getCtx();
        if (!ctx) { ambientState.nodes = null; return; }

        var now = ctx.currentTime;
        // Fade out tous les gains
        (nodes.gains || []).forEach(function (g) {
            try {
                g.gain.cancelScheduledValues(now);
                g.gain.setValueAtTime(g.gain.value, now);
                g.gain.linearRampToValueAtTime(0, now + fadeTime);
            } catch (e) { /* ignore */ }
        });
        // Arrêter les sources après le fade
        setTimeout(function () {
            (nodes.sources || []).forEach(function (s) {
                try { s.stop(); } catch (e) { /* ignore */ }
            });
            ambientState.nodes = null;
        }, (fadeTime + 0.2) * 1000);
    }

    function createLofiAmbient(ctx) {
        var v = vol('ambient');
        if (!v) return null;

        var sources = [], gains = [];

        // 1. Bruit rose filtré (vinyle)
        var bufLen = ctx.sampleRate * 2;
        var buf = ctx.createBuffer(1, bufLen, ctx.sampleRate);
        var data = buf.getChannelData(0);
        var b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
        for (var i = 0; i < bufLen; i++) {
            var white = Math.random() * 2 - 1;
            b0 = 0.99886 * b0 + white * 0.0555179;
            b1 = 0.99332 * b1 + white * 0.0750759;
            b2 = 0.96900 * b2 + white * 0.1538520;
            b3 = 0.86650 * b3 + white * 0.3104856;
            b4 = 0.55000 * b4 + white * 0.5329522;
            b5 = -0.7616 * b5 - white * 0.0168980;
            data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11;
            b6 = white * 0.115926;
        }
        var noise = ctx.createBufferSource();
        noise.buffer = buf;
        noise.loop = true;

        var lpf = ctx.createBiquadFilter();
        lpf.type = 'lowpass';
        lpf.frequency.value = 600;
        lpf.Q.value = 0.7;

        var noiseGain = ctx.createGain();
        noiseGain.gain.value = 0;

        noise.connect(lpf);
        lpf.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start();
        sources.push(noise);
        gains.push(noiseGain);

        // Fade in
        noiseGain.gain.linearRampToValueAtTime(0.04 * v, ctx.currentTime + CROSSFADE);

        // 2. Pad doux (C4‑E4‑G4 avec détune)
        [261.63, 329.63, 392.00].forEach(function (freq) {
            var osc  = ctx.createOscillator();
            var g    = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.value = freq;
            osc.detune.value = (Math.random() - 0.5) * 12;
            g.gain.value = 0;
            osc.connect(g);
            g.connect(ctx.destination);
            osc.start();
            sources.push(osc);
            gains.push(g);
            g.gain.linearRampToValueAtTime(0.025 * v, ctx.currentTime + CROSSFADE);
        });

        return { sources: sources, gains: gains };
    }

    function createEpicAmbient(ctx) {
        var v = vol('ambient');
        if (!v) return null;

        var sources = [], gains = [];

        // 1. Basse pulsante
        var bassOsc = ctx.createOscillator();
        var bassGain = ctx.createGain();
        bassOsc.type = 'sawtooth';
        bassOsc.frequency.value = 65.41; // C2
        bassGain.gain.value = 0;
        var bassLpf = ctx.createBiquadFilter();
        bassLpf.type = 'lowpass';
        bassLpf.frequency.value = 200;
        bassOsc.connect(bassLpf);
        bassLpf.connect(bassGain);
        bassGain.connect(ctx.destination);
        bassOsc.start();
        sources.push(bassOsc);
        gains.push(bassGain);
        bassGain.gain.linearRampToValueAtTime(0.06 * v, ctx.currentTime + CROSSFADE);

        // LFO sur la basse
        var lfo = ctx.createOscillator();
        var lfoGain = ctx.createGain();
        lfo.frequency.value = 0.5;
        lfoGain.gain.value = 0.03 * v;
        lfo.connect(lfoGain);
        lfoGain.connect(bassGain.gain);
        lfo.start();
        sources.push(lfo);
        gains.push(lfoGain);

        // 2. Pad large (C3‑E3‑G3‑B3)
        [130.81, 164.81, 196.00, 246.94].forEach(function (freq) {
            var osc = ctx.createOscillator();
            var g   = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.value = freq;
            osc.detune.value = (Math.random() - 0.5) * 8;
            g.gain.value = 0;
            osc.connect(g);
            g.connect(ctx.destination);
            osc.start();
            sources.push(osc);
            gains.push(g);
            g.gain.linearRampToValueAtTime(0.035 * v, ctx.currentTime + CROSSFADE);
        });

        // 3. Bruit blanc filtré très doux (souffle épique)
        var bufLen = ctx.sampleRate * 2;
        var buf = ctx.createBuffer(1, bufLen, ctx.sampleRate);
        var d = buf.getChannelData(0);
        for (var j = 0; j < bufLen; j++) d[j] = Math.random() * 2 - 1;
        var wn = ctx.createBufferSource();
        wn.buffer = buf;
        wn.loop = true;
        var hpf = ctx.createBiquadFilter();
        hpf.type = 'highpass';
        hpf.frequency.value = 4000;
        var wnGain = ctx.createGain();
        wnGain.gain.value = 0;
        wn.connect(hpf);
        hpf.connect(wnGain);
        wnGain.connect(ctx.destination);
        wn.start();
        sources.push(wn);
        gains.push(wnGain);
        wnGain.gain.linearRampToValueAtTime(0.015 * v, ctx.currentTime + CROSSFADE);

        return { sources: sources, gains: gains };
    }

    function startAmbient(name) {
        var ctx = getCtx();
        if (!ctx) return;
        if (name === 'lofi')  ambientState.nodes = createLofiAmbient(ctx);
        if (name === 'epic')  ambientState.nodes = createEpicAmbient(ctx);
    }

    function updateAmbientVolume() {
        var nodes = ambientState.nodes;
        if (!nodes) return;
        var v = vol('ambient');
        (nodes.gains || []).forEach(function (g, i) {
            try {
                // Premiers gains sont plus forts (noise/bass), les pads sont plus doux
                var base = i === 0 ? 0.04 : 0.025;
                if (ambientState.name === 'epic') base = i === 0 ? 0.06 : 0.035;
                g.gain.value = base * v;
            } catch (e) { /* ignore */ }
        });
    }

    function setAmbient(name) {
        name = name || 'silence';
        var oldName = ambientState.name;
        ambientState.name = name;
        prefs.currentAmbient = name;
        savePrefs();

        if (oldName !== 'silence') {
            stopAmbient(CROSSFADE);
        }
        if (name !== 'silence' && prefs.enabled) {
            // Petit délai si crossfade en cours
            var delay = (oldName !== 'silence') ? CROSSFADE * 0.4 * 1000 : 0;
            setTimeout(function () { startAmbient(name); }, delay);
        }
    }

    // ─── API publiques ─────────────────────────────────────────

    function setVolume(category, value) {
        value = Math.max(0, Math.min(1, Number(value) || 0));
        if (category === 'master')  prefs.masterVolume  = value;
        else if (category === 'ui')      prefs.uiVolume      = value;
        else if (category === 'game')    prefs.gameVolume    = value;
        else if (category === 'ambient') prefs.ambientVolume = value;
        if (category === 'ambient' || category === 'master') updateAmbientVolume();
        savePrefs();
    }

    function toggle(state) {
        prefs.enabled = (state !== undefined) ? !!state : !prefs.enabled;
        if (!prefs.enabled) stopAmbient(0.5);
        else if (prefs.currentAmbient !== 'silence') {
            setTimeout(function () { startAmbient(prefs.currentAmbient); }, 100);
        }
        savePrefs();
        return prefs.enabled;
    }

    function getPrefs() {
        var out = {};
        for (var k in prefs) out[k] = prefs[k];
        return out;
    }

    // ─── Auto‑clic UI ──────────────────────────────────────────
    document.addEventListener('click', function (e) {
        unlock();
        if (!e.target.closest) return;
        // Éviter le double‑son si le panneau son est la cible
        if (e.target.closest('#sm-panel')) return;

        // Pièces de la maison — intercepter <a> pour laisser le son jouer
        var roomEl = e.target.closest('.room-group, [data-room], svg a, .room-card');
        if (roomEl) {
            play('selectRoom');
            return;
        }

        var sel = 'button,.btn,a.btn,input[type="submit"],input[type="button"],' +
                  '.task-card,.avatar-square,.back-btn-glass,' +
                  '.burger-menu,.burger-nav-item,.burger-close,' +
                  '.dashboard-toggle,.dashboard-floating';
        if (e.target.closest(sel)) {
            play('buttonClick');
        }
    }, true);

    document.addEventListener('touchstart', unlock, { once: true });
    document.addEventListener('keydown', unlock, { once: true });

    // ─── Panneau de contrôle (injecté dans le DOM) ─────────────

    function injectPanel() {
        if (panelInjected) return;
        panelInjected = true;

        var css = document.createElement('style');
        css.textContent = [
            '#sm-panel-overlay{position:fixed;inset:0;z-index:9999;background:rgba(21,48,54,.55);',
            'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);',
            'display:none;align-items:center;justify-content:center;opacity:0;',
            'transition:opacity .25s ease}',
            '#sm-panel-overlay.open{display:flex;opacity:1}',

            '#sm-panel{background:linear-gradient(135deg,rgba(255,255,255,.92),rgba(166,211,220,.35));',
            'backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);',
            'border:1px solid rgba(255,255,255,.4);border-radius:24px;',
            'padding:28px 24px 22px;width:310px;max-width:90vw;',
            'box-shadow:0 20px 50px rgba(21,48,54,.3),inset 0 1px 0 rgba(255,255,255,.6);',
            'color:#153036;font-family:Montserrat,sans-serif;',
            'animation:sm-pop .35s cubic-bezier(.34,1.56,.64,1)}',
            '@keyframes sm-pop{0%{transform:scale(.85) translateY(20px);opacity:0}100%{transform:scale(1) translateY(0);opacity:1}}',

            '#sm-panel h3{margin:0 0 18px;font-size:17px;font-weight:700;text-align:center}',
            '#sm-panel .sm-close{position:absolute;top:12px;right:14px;background:rgba(21,48,54,.08);',
            'border:none;border-radius:50%;width:32px;height:32px;font-size:18px;cursor:pointer;',
            'display:flex;align-items:center;justify-content:center;color:#153036}',

            '.sm-row{display:flex;align-items:center;gap:10px;margin:10px 0;font-size:13px;font-weight:600}',
            '.sm-row label{min-width:72px}',
            '.sm-row input[type=range]{flex:1;accent-color:#597176;height:6px}',
            '.sm-row .sm-val{min-width:28px;text-align:right;font-size:12px;opacity:.7}',

            '.sm-toggle-row{display:flex;align-items:center;justify-content:space-between;margin:0 0 14px;padding-bottom:14px;border-bottom:1px solid rgba(21,48,54,.1)}',
            '.sm-switch{position:relative;width:44px;height:24px}',
            '.sm-switch input{opacity:0;width:0;height:0}',
            '.sm-switch .sm-slider{position:absolute;inset:0;background:#ccc;border-radius:24px;transition:.25s;cursor:pointer}',
            '.sm-switch .sm-slider:before{content:"";position:absolute;height:18px;width:18px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:.25s}',
            '.sm-switch input:checked+.sm-slider{background:#597176}',
            '.sm-switch input:checked+.sm-slider:before{transform:translateX(20px)}',

            '.sm-ambient-row{margin:14px 0 6px;font-size:13px;font-weight:600}',
            '.sm-ambient-btns{display:flex;gap:8px;margin-top:8px}',
            '.sm-ambient-btns button{flex:1;padding:8px 0;border-radius:14px;border:1px solid rgba(89,113,118,.25);',
            'background:rgba(255,255,255,.5);font-size:12px;font-weight:600;cursor:pointer;',
            'color:#153036;transition:all .2s}',
            '.sm-ambient-btns button.active{background:rgba(89,113,118,.25);border-color:#597176;color:#153036}'
        ].join('\n');
        document.head.appendChild(css);

        // Bouton flottant supprimé (panneau accessible via SoundManager.openPanel())

        // Overlay + panneau
        var overlay = document.createElement('div');
        overlay.id = 'sm-panel-overlay';
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) closePanel();
        });

        var panel = document.createElement('div');
        panel.id = 'sm-panel';
        panel.style.position = 'relative';
        panel.innerHTML = [
            '<button class="sm-close" aria-label="Fermer">&times;</button>',
            '<h3>🔊 Sons</h3>',

            '<div class="sm-toggle-row">',
            '  <span style="font-weight:700;font-size:14px">Sons activés</span>',
            '  <label class="sm-switch"><input type="checkbox" id="sm-enabled"><span class="sm-slider"></span></label>',
            '</div>',

            '<div class="sm-row"><label>Global</label>',
            '  <input type="range" min="0" max="100" id="sm-master">',
            '  <span class="sm-val" id="sm-master-val"></span></div>',

            '<div class="sm-row"><label>Interface</label>',
            '  <input type="range" min="0" max="100" id="sm-ui">',
            '  <span class="sm-val" id="sm-ui-val"></span></div>',

            '<div class="sm-row"><label>Jeu</label>',
            '  <input type="range" min="0" max="100" id="sm-game">',
            '  <span class="sm-val" id="sm-game-val"></span></div>',

            '<div class="sm-row"><label>Ambiance</label>',
            '  <input type="range" min="0" max="100" id="sm-ambient">',
            '  <span class="sm-val" id="sm-ambient-val"></span></div>',

            '<div class="sm-ambient-row">Ambiance de fond</div>',
            '<div class="sm-ambient-btns">',
            '  <button data-amb="silence">Silence</button>',
            '  <button data-amb="lofi">Lo-fi</button>',
            '  <button data-amb="epic">Épique</button>',
            '</div>'
        ].join('\n');

        overlay.appendChild(panel);
        document.body.appendChild(overlay);

        // ── Événements du panneau ──
        panel.querySelector('.sm-close').addEventListener('click', closePanel);

        var enEl     = panel.querySelector('#sm-enabled');
        var masterEl = panel.querySelector('#sm-master');
        var uiEl     = panel.querySelector('#sm-ui');
        var gameEl   = panel.querySelector('#sm-game');
        var ambEl    = panel.querySelector('#sm-ambient');

        enEl.addEventListener('change', function () { toggle(enEl.checked); });
        masterEl.addEventListener('input', function () { setVolume('master',  masterEl.value / 100); });
        uiEl.addEventListener('input',     function () { setVolume('ui',      uiEl.value / 100); });
        gameEl.addEventListener('input',   function () { setVolume('game',    gameEl.value / 100); });
        ambEl.addEventListener('input',    function () { setVolume('ambient', ambEl.value / 100); });

        panel.querySelectorAll('.sm-ambient-btns button').forEach(function (b) {
            b.addEventListener('click', function () { setAmbient(b.dataset.amb); });
        });

        syncPanel();
    }

    function syncPanel() {
        if (!panelInjected) return;
        var p = prefs;
        var el = function (id) { return document.getElementById(id); };
        var enEl = el('sm-enabled');
        if (enEl) enEl.checked = p.enabled;
        var masterEl = el('sm-master');
        if (masterEl) { masterEl.value = Math.round(p.masterVolume * 100); }
        var uiEl = el('sm-ui');
        if (uiEl) uiEl.value = Math.round(p.uiVolume * 100);
        var gameEl = el('sm-game');
        if (gameEl) gameEl.value = Math.round(p.gameVolume * 100);
        var ambEl = el('sm-ambient');
        if (ambEl) ambEl.value = Math.round(p.ambientVolume * 100);

        // Val labels
        var mv = el('sm-master-val'); if (mv) mv.textContent = Math.round(p.masterVolume * 100) + '%';
        var uv = el('sm-ui-val');     if (uv) uv.textContent = Math.round(p.uiVolume * 100) + '%';
        var gv = el('sm-game-val');   if (gv) gv.textContent = Math.round(p.gameVolume * 100) + '%';
        var av = el('sm-ambient-val');if (av) av.textContent = Math.round(p.ambientVolume * 100) + '%';

        // Ambient buttons
        var btns = document.querySelectorAll('.sm-ambient-btns button');
        btns.forEach(function (b) {
            b.classList.toggle('active', b.dataset.amb === p.currentAmbient);
        });

        // Bouton flottant icône
    }

    function openPanel() {
        injectPanel();
        syncPanel();
        var ov = document.getElementById('sm-panel-overlay');
        if (ov) {
            ov.style.display = 'flex';
            requestAnimationFrame(function () { ov.classList.add('open'); });
        }
    }

    function closePanel() {
        var ov = document.getElementById('sm-panel-overlay');
        if (ov) {
            ov.classList.remove('open');
            setTimeout(function () { ov.style.display = 'none'; }, 260);
        }
    }

    // ─── Initialisation ────────────────────────────────────────
    initHowlSounds();

    // Injecter le bouton flottant après le chargement DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { injectPanel(); });
    } else {
        injectPanel();
    }

    // Relancer l'ambiance si elle était active
    if (prefs.enabled && prefs.currentAmbient !== 'silence') {
        document.addEventListener('click', function resumeAmbient() {
            document.removeEventListener('click', resumeAmbient);
            unlock();
            setTimeout(function () { startAmbient(prefs.currentAmbient); }, 300);
        });
    }

    // ─── Exposition globale ────────────────────────────────────
    window.SoundManager = {
        play       : play,
        setVolume  : setVolume,
        toggle     : toggle,
        getPrefs   : getPrefs,
        setAmbient : setAmbient,
        openPanel  : openPanel,
        closePanel : closePanel,
        unlock     : unlock
    };

    // Aliases legacy (compatibilité avec le code existant)
    window.playClickSound      = function () { play('buttonClick'); };
    window.playSound           = function () { play('buttonClick'); };
    window.playSuccessSound    = function () { play('success'); };
    window.playNavSound        = function () { play('navigate'); };
    window.playRoomClickSound  = function () { play('selectRoom'); };
    window.playProgressSound   = function () { play('victory'); };
    window.playTaskCreatedSound = function () { play('buttonClick'); };
    window.playVictorySound    = function () { play('gainPoints'); };
    window.playMessageSound    = function () { play('receiveMessage'); };
    window.playSendSound       = function () { play('sendMessage'); };

    window.DustSounds = {
        click   : function () { play('buttonClick'); },
        success : function () { play('success'); },
        nav     : function () { play('navigate'); },
        roomZoom: function () { play('roomFullscreen'); }
    };

    console.log('🔊 SoundManager initialisé (v6)', 'enabled:', prefs.enabled, 'master:', prefs.masterVolume, 'ui:', prefs.uiVolume);
})();
