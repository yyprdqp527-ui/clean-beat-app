import io

lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/tasks.html', 'r', encoding='utf-8').readlines()
print("=== tasks.html CSS page-level elements (L90-165) ===")
for i in range(89, 170):
    print(f"L{i+1}: {lines[i].rstrip()[:180]}")

print()
print("=== tasks.html structure (CSS selector at L599-615) ===")
for i in range(598, 620):
    if i < len(lines):
        print(f"L{i+1}: {lines[i].rstrip()[:180]}")
