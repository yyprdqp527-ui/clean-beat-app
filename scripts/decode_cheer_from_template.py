#!/usr/bin/env python3
import re
import sys
from pathlib import Path
import base64

repo_root = Path(__file__).resolve().parents[1]
template = repo_root / 'templates' / 'task_page_enhanced.html'
out_dir = repo_root / 'static' / 'sounds'
out_file = out_dir / 'cheer.wav'

if not template.exists():
    print('Template not found:', template)
    sys.exit(2)

text = template.read_text(encoding='utf-8')
# find data URI base64 inside the audio tag
m = re.search(r'data:audio/\w+;base64,([A-Za-z0-9+/=\n\r]+)"', text)
if not m:
    print('No data:audio/...;base64, found in', template)
    sys.exit(3)

b64 = m.group(1)
# strip whitespace/newlines
b64 = ''.join(b64.split())

try:
    out_dir.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print('Could not create directory', out_dir, '–', e)
    print('You may need to run this script with elevated permissions or create the directory manually.')

try:
    data = base64.b64decode(b64)
    out_file.write_bytes(data)
    print('Wrote', out_file)
except Exception as e:
    print('Failed to write WAV file:', e)
    sys.exit(4)
