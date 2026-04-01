#!/usr/bin/env python3
"""Fix overflow:hidden on .cw-wrap that clips badges"""

with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# Fix 1: .cw-tabs - add overflow:visible
old_tabs = '.cw-tabs {\n    display: flex; width: 100%;\n    border-bottom: 1px solid rgba(21,48,54,0.06);\n    background: transparent;\n}'
new_tabs = '.cw-tabs {\n    display: flex; width: 100%;\n    border-bottom: 1px solid rgba(21,48,54,0.06);\n    background: transparent;\n    overflow: visible;\n}'

if old_tabs in content:
    content = content.replace(old_tabs, new_tabs)
    changes += 1
    print('OK: .cw-tabs overflow:visible added')
elif 'overflow: visible;' in content[content.find('.cw-tabs {'):content.find('.cw-tabs {')+200]:
    print('SKIP: .cw-tabs already has overflow:visible')
else:
    print('WARN: .cw-tabs pattern not found')

# Fix 2: .cw-wrap - change overflow:hidden to overflow:visible
# .cw-body already has its own overflow:hidden for the expandable section
old_overflow = '    overflow: hidden;\n}'
# Find specifically in .cw-wrap block
wrap_start = content.find('.cw-wrap {')
if wrap_start >= 0:
    wrap_end = content.find('\n}', wrap_start) + 2
    wrap_block = content[wrap_start:wrap_end]
    if 'overflow: hidden;' in wrap_block:
        new_block = wrap_block.replace('overflow: hidden;', 'overflow: visible;')
        content = content[:wrap_start] + new_block + content[wrap_end:]
        changes += 1
        print('OK: .cw-wrap overflow changed to visible')
    elif 'overflow: visible;' in wrap_block:
        print('SKIP: .cw-wrap already has overflow:visible')
    else:
        print('WARN: no overflow found in .cw-wrap')
else:
    print('ERROR: .cw-wrap not found')

if changes > 0:
    with open('templates/menu.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'\nFile saved with {changes} change(s).')
else:
    print('\nNo changes needed.')
