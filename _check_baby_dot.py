import io
lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html', 'r', encoding='utf-8').readlines()

# CSS for room-baby-dot
print("=== CSS .room-baby-dot (L1860-1900) ===")
for i in range(1859, 1900):
    print(f"L{i+1}: {lines[i][:180].rstrip()}")

# HTML full context around room-baby-dot (L4795-4815)
print()
print("=== HTML rooms-isometric (L4793-4820) ===")
for i in range(4792, 4820):
    print(f"L{i+1}: {lines[i][:200].rstrip()}")

# Check if room-baby-dot has a category condition
print()
print("=== room-baby-dot with context (any condition?) ===")
for i, l in enumerate(lines, 1):
    if 'room-baby-dot' in l and 'span' in l:
        # Print 5 lines of context
        for j in range(max(0, i-3), min(len(lines), i+3)):
            print(f"L{j+1}: {lines[j][:200].rstrip()}")
        print()
