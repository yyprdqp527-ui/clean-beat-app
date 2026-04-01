from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))
t = env.get_template('classement.html')
players = [
    {'name':'Alice','email':'a@a.com','daily_points':10,'daily_tasks':3,
     'weekly_points':25,'weekly_tasks':8,'monthly_points':60,'monthly_tasks':20,
     'is_current_user':True,'avatar_file':None,'avatar_url':None,'avatar':None,
     'player_color_hex':'#ff0000','skull_active':False,'skull_pending':False,'skull_count':0},
]
try:
    html = t.render(players=players, current_user_name='a@a.com', house_name='Test')
    for pid in ['podium-today','podium-week','podium-month','podium-view active']:
        print(f"{'OK' if pid in html else 'MANQUANT'}: {pid}")
    print(f"HTML size: {len(html)}")
except Exception as e:
    print(f"ERREUR: {e}")
    import traceback; traceback.print_exc()
