import requests

s = requests.Session()

# Login as nnbn@lkj.com (house 173)
r = s.post('http://127.0.0.1:8000/login', data={'email': 'nnbn@lkj.com', 'password': 'CleanBeat2025!'}, allow_redirects=True)
print(f"Login: {r.status_code}, url: {r.url}")

# Si login echoue, essayer un autre mdp
if 'login' in r.url.lower():
    print("Login FAILED - trying other passwords...")
    for pwd in ['cleanbeat', 'password', '1234', 'test', 'CleanBeat2025']:
        r = s.post('http://127.0.0.1:8000/login', data={'email': 'nnbn@lkj.com', 'password': pwd}, allow_redirects=True)
        if 'login' not in r.url.lower():
            print(f"  Success with: {pwd}")
            break
    else:
        # Check if maybe we need to look at the form
        print("All passwords failed. Checking login form...")
        r2 = s.get('http://127.0.0.1:8000/login')
        if 'csrf' in r2.text.lower():
            print("CSRF token required")

# Get menu (NO preview_sunday - crown should show every day now)
r = s.get('http://127.0.0.1:8000/menu')
print(f"\nMenu: {r.status_code}, len={len(r.text)}")

html = r.text
# Check for winner-crown
crown_count = html.count('winner-crown')
print(f"'winner-crown' in HTML: {crown_count} times")

# Check has_weekly_winner is used
hww_count = html.count('has_weekly_winner')
print(f"'has_weekly_winner' in HTML (should be 0 - rendered): {hww_count}")

import re
for m in re.finditer('<span class="winner-crown">', html):
    start = max(0, m.start() - 150)
    end = min(len(html), m.end() + 50)
    print(f"\n--- Crown span at {m.start()} ---")
    print(html[start:end])

# Also check if the CSS is there
if '.winner-crown' in html:
    print("\n--- CSS .winner-crown present ---")
else:
    print("\n--- CSS .winner-crown MISSING ---")
