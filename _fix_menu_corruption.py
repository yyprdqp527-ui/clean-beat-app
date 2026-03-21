#!/usr/bin/env python3
"""
Fix menu.html corruption - remove duplicate updateUnreadBadge code block
"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Marker pour la corruption : "lectureburger-nav-icon"
corruption_marker = "lectureburger-nav-icon"

if corruption_marker in content:
    # Trouve l'index de la corruption
    idx = content.find(corruption_marker)
    print(f"✅ Corruption trouvée à l'index {idx}")
    
    # Extraire 200 caractères avant et après pour contexte
    before = content[max(0, idx-200):idx]
    after = content[idx:min(len(content), idx+600)]
    
    print("\n=== AVANT LA CORRUPTION ===")
    print(before)
    print("\n=== CORRUPTION + APRÈS ===")
    print(after)
    
    # La corruption commence après "de lecture" et se termine avant "window.__unreadBySender"
    # On cherche le pattern exact
    
    # Trouver le début : "// Caches locaux des compteurs pour fusionner les deux sens de lecture"
    start_pattern = "// Caches locaux des compteurs pour fusionner les deux sens de lecture"
    start_idx = content.find(start_pattern, idx-100)
    
    if start_idx == -1:
        print("❌ Pattern de début non trouvé")
        exit(1)
    
    # Trouver la fin : "window.__unreadBySender = window.__unreadBySender || {};"
    end_pattern = "window.__unreadBySender = window.__unreadBySender || {};"
    end_idx = content.find(end_pattern, start_idx)
    
    if end_idx == -1:
        print("❌ Pattern de fin non trouvé")
        exit(1)
    
    # Extraire le bloc corrompu
    corrupted_block = content[start_idx:end_idx]
    print(f"\n=== BLOC CORROMPU ({len(corrupted_block)} chars) ===")
    print(corrupted_block[:500])
    
    # Créer le bloc nettoyé
    clean_block = """// Caches locaux des compteurs pour fusionner les deux sens de lecture
                window.__unreadBySender = window.__unreadBySender || {};
                """
    
    # Remplacer
    new_content = content[:start_idx] + clean_block + content[end_idx:]
    
    # Vérifier qu'il n'y a qu'une seule occurrence de updateUnreadBadge maintenant
    count = new_content.count("function updateUnreadBadge(count)")
    print(f"\n✅ Nombre d'occurrences de 'function updateUnreadBadge' après nettoyage: {count}")
    
    if count != 1:
        print(f"❌ ERREUR: devrait avoir 1 occurrence, mais en a {count}")
        exit(1)
    
    # Sauvegarder
    with open('templates/menu.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"\n✅ Fichier nettoyé ! Supprimé {len(corrupted_block) - len(clean_block)} characters")
    
else:
    print("❌ Corruption non trouvée (pas de 'lectureburger-nav-icon')")
    print("Le fichier est peut-être déjà propre ou la corruption est différente")
