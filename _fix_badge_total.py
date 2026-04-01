path = 'templates/menu.html'
lines = open(path, encoding='utf-8').readlines()

# Remplacer lignes 6172-6175 (0-indexed: 6171-6174)
expected = [
    '                        var _total = (_sc.unread_received > 0 ? 1 : 0)\n',
    '                                   + (_sc.unread_baby > 0 ? 1 : 0)\n',
    '                                   + (_sc.courses_pending_count > 0 ? 1 : 0)\n',
    '                                   + (_sc.pending_missions_count > 0 ? 1 : 0);\n',
]

actual = lines[6171:6175]
if actual == expected:
    replacement = [
        '                        // Badge icone PWA : seulement messages + bebe\n',
        '                        // courses et missions exclus (taches permanentes, pas nouvelles notifs)\n',
        '                        var _total = (_sc.unread_received > 0 ? 1 : 0)\n',
        '                                   + (_sc.unread_baby > 0 ? 1 : 0);\n',
    ]
    lines[6171:6175] = replacement
    open(path, 'w', encoding='utf-8').writelines(lines)
    print('OK fix applique')
else:
    print('MISMATCH')
    for i, l in enumerate(actual):
        print(f'  Got    {repr(l)}')
        print(f'  Expect {repr(expected[i])}')
