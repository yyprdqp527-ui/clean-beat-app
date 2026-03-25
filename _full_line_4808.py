import io
lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html', 'r', encoding='utf-8').readlines()

# Full content of L4808 (0-indexed: 4807)
print("=== Full line 4808 ===")
print(repr(lines[4807]))

# Check: is there a category condition around room-baby-dot?
for i, l in enumerate(lines, 1):
    if 'room-baby-dot' in l:
        # Print from i-5 to i+3
        for j in range(max(0, i-6), min(len(lines), i+4)):
            print(f"L{j+1}: {repr(lines[j][:300])}")
        print()
