import io
lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/base.html', 'r', encoding='utf-8').readlines()
print(f"Total lines: {len(lines)}")
print()
print("=== Bloc CSS adaptatif (L42-90) ===")
for i in range(41, 92):
    if i < len(lines):
        print(f"L{i+1}: {lines[i].rstrip()[:200]}")
