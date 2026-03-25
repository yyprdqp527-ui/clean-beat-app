import io
lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html', 'r', encoding='utf-8').readlines()

# Lire le contexte complet autour de refreshMissionDots (lignes 5980-6015)
print("=== refreshMissionDots (lignes 5980-6020) ===")
for i in range(5979, min(6020, len(lines))):
    print(f"L{i+1}: {lines[i][:180].rstrip()}")

print()
print("=== room-card avec data-category (HTML) ===")
for i, l in enumerate(lines, 1):
    if 'data-category' in l and 'room-card' in l:
        print(f"L{i}: {l[:200].rstrip()}")
