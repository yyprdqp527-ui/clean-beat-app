import io
lines = io.open('/Users/anne-gaelledaval/Downloads/Appli web-2/templates/menu.html', 'r', encoding='utf-8').readlines()

# Context around line 5190 (refreshMissionDots call in WebSocket)
print("=== Context L5185-5200 (WS refreshMissionDots) ===")
for i in range(5184, 5200):
    print(f"L{i+1}: {lines[i][:180].rstrip()}")

# Also show the second refreshMissionDots call context (L5320-5345)
print()
print("=== Context L5308-5345 ===")
for i in range(5307, 5345):
    print(f"L{i+1}: {lines[i][:180].rstrip()}")

# Show the baby_badge_update WS listener and surrounding
print()
print("=== baby_badge_update WS listener (L6038-6060) ===")
for i in range(6037, 6065):
    print(f"L{i+1}: {lines[i][:180].rstrip()}")
