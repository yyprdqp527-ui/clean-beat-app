#!/usr/bin/env python3
"""Fix visibilitychange: reload after 5s in background instead of just fetch."""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the old visibilitychange block
old_marker = "Rafraichir quand la page redevient visible"
idx = content.find(old_marker)
assert idx != -1, "Marker not found"

# Go back to find the start of the comment line (// ...)
line_start = content.rfind('\n', 0, idx) + 1

# Find the end: the closing });  of the addEventListener
# Starting from the addEventListener, find the matching });
search_from = content.find("document.addEventListener('visibilitychange'", idx)
assert search_from != -1, "addEventListener not found"

# Find the closing }); — count braces
brace_count = 0
end_idx = search_from
found_first = False
for i in range(search_from, len(content)):
    if content[i] == '{':
        brace_count += 1
        found_first = True
    elif content[i] == '}':
        brace_count -= 1
        if found_first and brace_count == 0:
            # Found the closing } of the function
            # Now find the ); after it
            rest = content[i+1:i+10].lstrip()
            if rest.startswith(');'):
                end_idx = content.find(');', i+1) + 2
            else:
                end_idx = i + 1
            break

print(f"Replacing from pos {line_start} to {end_idx}")
print(f"Old block ({end_idx - line_start} chars):")
print(content[line_start:end_idx][:200])
print("...")

new_block = """                // \u2705 FIX iOS PWA : quand l'app reprend apr\u00e8s >5s en arri\u00e8re-plan,
                // forcer un rechargement complet pour obtenir les badges Jinja frais.
                // Sur iOS, taper l'ic\u00f4ne PWA d\u00e9clenche visibilitychange (pas pageshow),
                // et la page gel\u00e9e n'a aucune pastille si les notifs arrivent pendant le gel.
                var _cbHiddenAt = Date.now();
                document.addEventListener('visibilitychange', function() {
                    if (document.visibilityState === 'hidden') {
                        _cbHiddenAt = Date.now();
                    }
                    if (document.visibilityState === 'visible') {
                        var elapsed = Date.now() - _cbHiddenAt;
                        console.log('\U0001f504 Page redevenue visible apr\u00e8s ' + Math.round(elapsed/1000) + 's');
                        if (elapsed > 5000) {
                            // Plus de 5 secondes en arri\u00e8re-plan \u2192 page probablement p\u00e9rim\u00e9e
                            // Recharger pour obtenir les valeurs SSR fra\u00eeches (badges, missions, etc.)
                            window.location.reload();
                            return;
                        }
                        // Moins de 5s (simple changement d'onglet) \u2192 fetch suffit
                        window.refreshAllBadges();
                        if (window.refreshMissionDots) window.refreshMissionDots();
                        if (typeof updatePlayersPointsMenu === 'function') updatePlayersPointsMenu();
                    }
                });"""

content = content[:line_start] + new_block + content[end_idx:]

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n\u2705 visibilitychange fix\u00e9 : reload apr\u00e8s 5s en arri\u00e8re-plan")
