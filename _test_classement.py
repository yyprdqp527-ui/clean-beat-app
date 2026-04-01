import sys
sys.path.insert(0, '.')
from app import app
with app.test_client() as c:
    # Login
    rv = c.post('/login', data={'email':'a@me.com','password':'1'}, follow_redirects=True)
    print('Login status:', rv.status_code)
    # Get classement
    rv = c.get('/classement')
    print('Classement status:', rv.status_code)
    html = rv.data.decode('utf-8')
    for kw in ['podium-today','podium-week','podium-month','podium-view active','filter-btn','tab-today','tab-week','tab-month','loadCWTasks']:
        print(f"  {'OK' if kw in html else 'MANQUANT'}: {kw}")
    if rv.status_code == 500:
        print(html[:2000])
