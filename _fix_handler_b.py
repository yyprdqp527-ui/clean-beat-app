#!/usr/bin/env python3
"""Remove duplicate Handler B malus animation from menu.html"""

f = open('templates/menu.html', 'r', encoding='utf-8')
lines = f.readlines()
f.close()

# Replace lines 4778-4875 (1-indexed) with simplified version
new_block = """\
                    // Animer les barres de progression avec son au chargement
                    setTimeout(() => {
                        // Handler A gere deja malus/gain - on nettoie juste l'URL ici
                        const urlParams = new URLSearchParams(window.location.search);
                        if (urlParams.has('ts')) {
                            setTimeout(() => {
                                if (window.history && window.history.replaceState) {
                                    window.history.replaceState({}, document.title, window.location.pathname);
                                }
                            }, 2000);
                        }
                        animateProgressBar();
                    }, 500);
"""

new_lines = [l + '\n' for l in new_block.split('\n')]
# Remove trailing empty line from split
if new_lines and new_lines[-1] == '\n':
    new_lines = new_lines[:-1]

lines[4777:4875] = new_lines

f = open('templates/menu.html', 'w', encoding='utf-8')
f.writelines(lines)
f.close()
print(f'Done: replaced lines 4778-4875 with {len(new_lines)} lines')
