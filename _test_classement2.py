import sys
sys.path.insert(0, '.')
from app import app
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['user'] = 'a@me.com'
    rv = c.get('/classement')
    print('Status:', rv.status_code)
    html = rv.data.decode('utf-8')
    for kw in ['podium-today','podium-week','podium-month','podium-view active','filter-btn','tab-today','tab-week','tab-month','loadCWTasks']:
        print(f"  {'OK' if kw in html else 'MANQUANT'}: {kw}")
    if rv.status_code >= 400:
        print(html[:3000])
