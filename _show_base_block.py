import io

path = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates/base.html'
lines = io.open(path, 'r', encoding='utf-8').readlines()

# Show context around the ULTRA block (L42-90)
print("=== base.html L42-90 ===")
for i in range(41, 90):
    print(f"L{i+1}: {repr(lines[i][:200])}")
