import re, os

base = '/Users/anne-gaelledaval/Downloads/Appli web-2/templates'
for fname in ['rewards.html', 'task_page_enhanced.html', 'sats.html']:
    path = os.path.join(base, fname)
    with open(path) as f:
        c = f.read()
    blocks = re.findall(r'<style[^>]*>(.*?)</style>', c, re.DOTALL)
    jinja = sum(bool(re.search(r'\{\{|\{%', s)) for s in blocks)
    size = sum(len(s) for s in blocks)
    print(f'{fname}: {size//1024}KB CSS inline, {jinja} blocs avec Jinja')
