with open('templates/menu.html', 'r', encoding='utf-8') as f:
    content = f.read()

count = content.count('.room-baby-dot {')
print(f"Occurrences avant: {count}")

if count >= 2:
    first = content.find('.room-baby-dot {')
    second = content.find('.room-baby-dot {', first + 1)
    # Trouver le debut du bloc (le commentaire qui precede)
    block_start = content.rfind('/* Pastille rose', 0, second)
    # Trouver la fin du bloc (la prochaine } apres second)
    close = content.find('\n        }', second)
    block_end = close + len('\n        }')
    # Verifier aussi le \n\n avant le commentaire
    pre_newlines = content.rfind('\n\n', 0, block_start)
    if pre_newlines == block_start - 2:
        block_start = pre_newlines
    content = content[:block_start] + content[block_end:]
    print(f"Doublon supprime")
    print(f"Occurrences apres: {content.count('.room-baby-dot {')}")
else:
    print("Pas de doublon")

with open('templates/menu.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Sauvegarde OK")
