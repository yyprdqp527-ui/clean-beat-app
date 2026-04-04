import requests

s = requests.Session()
# Login
r = s.post('http://127.0.0.1:8000/login', data={'email': 'nnbn@lkj.com', 'password': 'CleanBeat2025!'}, allow_redirects=True)
print(f"Login status: {r.status_code}, url: {r.url}")

# Get menu with preview_sunday
r = s.get('http://127.0.0.1:8000/menu?preview_sunday=1')
print(f"Menu status: {r.status_code}")

# Check for winner-crown in HTML
html = r.text
count = html.count('winner-crown')
print(f"'winner-crown' found {count} times in HTML")

# Find context around each occurrence
import re
for m in re.finditer('winner-crown', html):
    start = max(0, m.start() - 100)
    end = min(len(html), m.end() + 100)
    print(f"\n--- occurrence at {m.start()} ---")
    print(html[start:end])
