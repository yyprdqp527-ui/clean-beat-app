/* ══════════════════════════════════════════════════════════════
   nav-feedback.js — feedback de navigation + anti-double-clic
   Cible: .back-btn-glass (flèches retour) et .qfq-tab (barre menu)
   - Affiche un état visuel "navigation en cours" instantanément
   - Empêche les clics répétés (cause majeure de saturation serveur)
   - Spinner discret après 250 ms si la page tarde à charger
   - Auto-reset si l'utilisateur revient via l'historique (bfcache)
   ══════════════════════════════════════════════════════════════ */
(function() {
    'use strict';

    // Sélecteurs ciblés (uniquement boutons identifiés comme lents)
    var SELECTOR = '.back-btn-glass, .qfq-tab';

    // Durée pendant laquelle un bouton reste "désactivé" même si
    // la navigation n'a pas encore eu lieu (anti-spam clics)
    var LOCK_MS = 1500;

    // Délai avant affichage du spinner (perception fluide < 250 ms)
    var SPINNER_DELAY_MS = 250;

    var navigationInProgress = false;
    var spinnerTimer = null;

    function markLoading(el) {
        if (!el || el.classList.contains('nav-loading')) return;
        el.classList.add('nav-loading');
        // Sauvegarder pour pouvoir reset si bfcache
        el.setAttribute('data-nav-locked', '1');

        // Afficher spinner après 250 ms si toujours sur la page
        if (spinnerTimer) clearTimeout(spinnerTimer);
        spinnerTimer = setTimeout(function() {
            if (el.classList.contains('nav-loading')) {
                el.classList.add('nav-loading-show-spinner');
            }
        }, SPINNER_DELAY_MS);

        // Filet de sécurité : si la navigation échoue (offline, erreur réseau),
        // déverrouiller au bout de LOCK_MS pour permettre un nouveau clic
        setTimeout(function() {
            unmarkLoading(el);
        }, LOCK_MS);
    }

    function unmarkLoading(el) {
        if (!el) return;
        el.classList.remove('nav-loading');
        el.classList.remove('nav-loading-show-spinner');
        el.removeAttribute('data-nav-locked');
        navigationInProgress = false;
    }

    function unmarkAll() {
        var locked = document.querySelectorAll('[data-nav-locked="1"]');
        for (var i = 0; i < locked.length; i++) {
            unmarkLoading(locked[i]);
        }
        if (spinnerTimer) {
            clearTimeout(spinnerTimer);
            spinnerTimer = null;
        }
        navigationInProgress = false;
    }

    function handleClick(e) {
        var target = e.target;
        // Remonter l'arbre pour trouver le bouton/lien
        while (target && target !== document.body) {
            if (target.matches && target.matches(SELECTOR)) {
                break;
            }
            target = target.parentElement;
        }
        if (!target || target === document.body) return;

        // Si une navigation est déjà en cours OU bouton déjà locké → bloquer
        if (navigationInProgress || target.classList.contains('nav-loading')) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }

        navigationInProgress = true;
        markLoading(target);
        // On NE preventDefault PAS : on laisse le navigateur naviguer
        // normalement. Le visuel s'affiche pendant que la requête part.
    }

    // Capture phase : on intercepte AVANT les autres handlers (onclick=)
    // pour bien bloquer les double-clics même si l'élément a un onclick inline
    document.addEventListener('click', handleClick, true);
    document.addEventListener('touchstart', function(e) {
        // Sur mobile, le touch est le premier signal — on peut commencer
        // à afficher le feedback dès le touch (latence perçue ≈ 0)
        var target = e.target;
        while (target && target !== document.body) {
            if (target.matches && target.matches(SELECTOR)) {
                if (!target.classList.contains('nav-loading') && !navigationInProgress) {
                    // Petit délai pour différencier scroll vs tap
                    setTimeout(function() {
                        // Si le clic suit, le handler click prendra le relais
                    }, 0);
                }
                return;
            }
            target = target.parentElement;
        }
    }, { passive: true, capture: true });

    // Si l'utilisateur revient via "back" du navigateur (bfcache),
    // on reset l'état (sinon les boutons restent grisés)
    window.addEventListener('pageshow', function(e) {
        if (e.persisted) {
            // Page restaurée depuis le cache → reset complet
            unmarkAll();
        }
    });

    // Si la page perd le focus (autre onglet/app), reset après retour
    window.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            // Au retour sur l'onglet, déverrouiller pour permettre
            // une nouvelle action immédiate
            setTimeout(unmarkAll, 100);
        }
    });

    // Reset au déchargement (sécurité : avant départ vers nouvelle page)
    window.addEventListener('beforeunload', function() {
        // Ne rien faire ici : on veut que l'état "loading" reste visible
        // pendant le chargement de la page suivante.
        // Le pageshow/load de la page suivante remettra à zéro.
    });

})();
