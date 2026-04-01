#!/usr/bin/env python3
"""Remove the debug banner from menu.html."""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = '<!-- \U0001f527 DEBUG V3'
end_marker = '</script>\n'

start_idx = content.find(start_marker)
if start_idx == -1:
    print("Debug banner not found, already removed?")
    import sys; sys.exit(0)

# Find the matching </script> after the debug block
search_from = content.find('<script>', start_idx)
end_idx = content.find('</script>', search_from) + len('</script>\n')

print(f"Removing debug banner: pos {start_idx} to {end_idx} ({end_idx - start_idx} chars)")
print(f"Start: {repr(content[start_idx:start_idx+60])}")
print(f"End: {repr(content[end_idx-40:end_idx])}")

content = content[:start_idx] + content[end_idx:]

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\u2705 Bandeau debug supprim\u00e9")
