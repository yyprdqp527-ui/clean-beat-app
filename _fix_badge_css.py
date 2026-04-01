#!/usr/bin/env python3
"""Fix: Améliorer la visibilité du badge dans la nav bar"""

with open('templates/menu.html', 'r') as f:
    content = f.read()

old = """.cw-tab-badge {
    position: absolute; top: 5px; right: calc(50% - 14px);
    background: #e74c3c; color: white; font-size: 9px; font-weight: 800;
    min-width: 14px; height: 14px; border-radius: 99px;
    display: flex; align-items: center; justify-content: center;
    padding: 0 3px; line-height: 1;
}"""

new = """.cw-tab-badge {
    position: absolute; top: -4px; right: -6px;
    background: linear-gradient(135deg, #ff4444 0%, #ff6b6b 100%);
    color: white; font-size: 10px; font-weight: 800;
    min-width: 18px; height: 18px; border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    padding: 0 5px; line-height: 1;
    z-index: 10;
    border: 1.5px solid white;
    box-shadow: 0 2px 8px rgba(255, 68, 68, 0.6);
    animation: pulse-badge 2s ease-in-out infinite;
}"""

count = content.count(old)
print(f"Found {count} occurrence(s) of old CSS")
assert count == 1, f"Expected 1, found {count}"

content = content.replace(old, new)

with open('templates/menu.html', 'w') as f:
    f.write(content)

print("✅ CSS badge fix applied!")
print("Changes:")
print("  - top: 5px → -4px (badge dépasse l'icône, plus visible)")
print("  - right: calc(50%-14px) → -6px (coin supérieur droit)")
print("  - taille: 14px → 18px")
print("  - gradient + border + shadow + animation pulse")
