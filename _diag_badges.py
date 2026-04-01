#!/usr/bin/env python3
with open('templates/menu.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def show_fn(name, extra=60):
    for i, l in enumerate(lines):
        if name in l:
            print(f"\n=== {name} (L{i+1}) ===")
            for j in range(i, min(i+extra, len(lines))):
                print(f"L{j+1}: {lines[j].rstrip()[:160]}")
            return
    print(f"\n=== {name} : INTROUVABLE ===")

show_fn('function updateUnreadBadge', 35)
show_fn('function updateAppBadge', 15)
show_fn('function refreshAllBadges', 70)
show_fn('function refreshMissionDots', 40)
