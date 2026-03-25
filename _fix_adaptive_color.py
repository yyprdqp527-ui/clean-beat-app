import io

path = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/base.html'
with io.open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# =====================================================================
# Bloc a supprimer (lignes 43-82 inclus, du commentaire ULTRA jusqu'aux exceptions)
# =====================================================================
OLD_BLOCK = """        /* ══════════════════════════════════════════════════════════════════
           🚨 RÈGLE CSS ULTRA-PUISSANTE D'ADAPTATION AUTOMATIQUE  
           ══════════════════════════════════════════════════════════════════ */
        
        /* Variables CSS adaptatives pour toute l'application */
        :root {
            --adaptive-text: {% if bg_theme_light %}#153036{% else %}#ffffff{% endif %};
            --adaptive-muted: {% if bg_theme_light %}rgba(21,48,54,0.7){% else %}rgba(255,255,255,0.7){% endif %};
            --adaptive-light: {% if bg_theme_light %}rgba(21,48,54,0.5){% else %}rgba(255,255,255,0.5){% endif %};
        }
        
        /* FORCE ADAPTATION SUR TOUS LES ÉLÉMENTS SANS EXCEPTION */
        * {
            color: var(--adaptive-text) !important;
        }
        
        /* Adaptation automatique du fond pour TOUTE l'application */
        body, .auto-adapt-text {
            background: {{ bg_gradient }} !important;
            color: var(--adaptive-text) !important;
        }
        
        /* Classes utilitaires pour adaptation forcée */
        .text-adaptive { color: var(--adaptive-text) !important; }
        .text-adaptive-muted { color: var(--adaptive-muted) !important; }
        .text-adaptive-light { color: var(--adaptive-light) !important; }
        
        /* EXCEPTIONS: Éléments qui doivent garder leurs couleurs spécifiques */
        .keep-color,
        [style*="background"],
        .gw-pts,
        .daily-chip,
        .avatar-points,
        .room-card-badge,
        .btn-primary,
        .btn-success,
        .btn-warning,
        .btn-danger {
            color: initial !important;
        }"""

# =====================================================================
# Nouveau bloc : ciblé, sans règle globale destructrice
# =====================================================================
NEW_BLOCK = """        /* ── Adaptation couleur texte selon le thème choisi (clair/sombre) ── */
        :root {
            --adaptive-text: {% if bg_theme_light %}#153036{% else %}#ffffff{% endif %};
            --adaptive-muted: {% if bg_theme_light %}rgba(21,48,54,0.7){% else %}rgba(255,255,255,0.7){% endif %};
            --adaptive-light: {% if bg_theme_light %}rgba(21,48,54,0.5){% else %}rgba(255,255,255,0.5){% endif %};
        }

        /* Classes utilitaires explicites pour le texte adaptatif */
        .text-adaptive { color: var(--adaptive-text) !important; }
        .text-adaptive-muted { color: var(--adaptive-muted) !important; }
        .text-adaptive-light { color: var(--adaptive-light) !important; }

        /* ── Éléments à fond propre CLAIR : texte toujours foncé, peu importe le thème ── */
        /* Inputs, textareas, selects : fond blanc/clair natif → texte foncé obligatoire */
        input, textarea, select, [contenteditable] {
            color: #153036 !important;
        }
        /* Cartes à fond blanc : le texte garde sa couleur propre (non overridée) */
        .task-card:not(.negative-task),
        .task-card:not(.negative-task) .task-name,
        .room-header,
        .room-header .room-name,
        .room-header .room-subtitle,
        .glass-card, .glass-panel, .glass-modal,
        .back-btn-glass,
        .header-menu {
            color: #153036 !important;
        }
        /* Sous-textes de cartes claires */
        .task-card:not(.negative-task) .task-subtitle,
        .task-card:not(.negative-task) .task-desc,
        .task-card:not(.negative-task) .task-points {
            color: #597176 !important;
        }"""

if OLD_BLOCK in content:
    content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)
    print("Remplacement du bloc ULTRA-PUISSANT effectué")
else:
    print("ERREUR: bloc OLD non trouvé - vérifier le texte exact")
    # Debug: find the closest match
    idx = content.find("RÈGLE CSS ULTRA-PUISSANTE")
    if idx >= 0:
        print("Trouvé à l'index", idx)
        print(repr(content[idx-20:idx+200]))
    else:
        idx = content.find("adaptive-text")
        if idx >= 0:
            print("adaptive-text trouvé à index", idx)
            print(repr(content[max(0, idx-100):idx+300]))

with io.open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fichier base.html sauvegardé")
