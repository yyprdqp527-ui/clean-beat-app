import io
lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html', 'r', encoding='utf-8').readlines()

print("=== ALL occurrences of refreshMissionDots ===")
for i, l in enumerate(lines, 1):
    if 'refreshMissionDots' in l:
        print(f"L{i}: {l[:180].rstrip()}")

print()
print("=== ALL occurrences of refreshAllBadges ===")
for i, l in enumerate(lines, 1):
    if 'refreshAllBadges' in l:
        print(f"L{i}: {l[:180].rstrip()}")

print()
print("=== WS events that trigger badge refresh ===")
for i, l in enumerate(lines, 1):
    if 'socket.on' in l:
        print(f"L{i}: {l[:180].rstrip()}")
