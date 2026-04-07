# routes/websocket.py
"""WebSocket event handlers — synchronisation temps réel."""

from flask import request
from flask_socketio import join_room, emit


def register_websocket_events(socketio):
    """Enregistre les événements WebSocket sur l'instance socketio fournie."""

    @socketio.on('connect')
    def handle_connect():
        """Connexion d'un client WebSocket"""
        from app import _dbg
        _dbg(f'🔌 Client connecté: {request.sid}')

    @socketio.on('disconnect')
    def handle_disconnect():
        """Déconnexion d'un client WebSocket"""
        from app import _dbg
        _dbg(f'❌ Client déconnecté: {request.sid}')

    @socketio.on('join_house')
    def handle_join_house(data):
        """Un joueur rejoint la room de sa maison"""
        from app import _dbg, get_db_connection
        user_email = data.get('email')
        _dbg(f'📩 join_house reçu : email={user_email}, sid={request.sid}')

        if not user_email:
            _dbg(f'⚠️ join_house : email manquant !')
            return

        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT house_id FROM users WHERE email=?", (user_email,))
            row = c.fetchone()
            conn.close()

            if row and row[0]:
                house_id = row[0]
                room = f"house_{house_id}"
                join_room(room)
                emit('joined_room', {'room': room, 'email': user_email})
                _dbg(f'✅ {user_email} (sid={request.sid}) a REJOINT la room {room}')
                _dbg(f'   🔍 Clients dans la room : utiliser socketio.server.manager.rooms pour voir')
            else:
                _dbg(f'⚠️ {user_email} : house_id introuvable !')
        except Exception as e:
            _dbg(f'❌ Erreur join_house pour {user_email}: {e}')

    @socketio.on('points_updated')
    def handle_points_updated(data):
        """Diffuser la mise à jour des points à tous les joueurs de la maison"""
        from app import _dbg, get_db_connection
        try:
            user_email = data.get('email')
            if not user_email:
                return

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT house_id FROM users WHERE email=?", (user_email,))
            row = c.fetchone()

            if row and row[0]:
                house_id = row[0]
                room = f"house_{house_id}"

                # Récupérer les points de tous les joueurs de la maison
                c.execute("""
                    SELECT u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points,
                           COALESCE(SUM(ct.points), 0) as daily_points
                    FROM users u
                    LEFT JOIN completed_tasks ct ON u.email = ct.user_email
                        AND DATE(ct.completed_at) = DATE('now')
                    WHERE u.house_id = ?
                    GROUP BY u.email, u.name, u.avatar, u.avatar_url, u.avatar_file, u.points
                    ORDER BY daily_points DESC, u.points DESC
                """, (house_id,))
                players = []
                for p in c.fetchall():
                    players.append({
                        'email': p[0],
                        'name': p[1],
                        'avatar': p[2],
                        'avatar_url': p[3],
                        'avatar_file': p[4],
                        'total_points': p[5] or 0,
                        'daily_points': int(p[6]) if p[6] else 0
                    })

                conn.close()

                # Diffuser à tous les clients de la room
                emit('players_points_update', {'players': players}, room=room)
                _dbg(f'📊 Points mis à jour pour la room {room}')
        except Exception as e:
            _dbg(f'❌ Erreur points_updated: {e}')

    @socketio.on('avatar_updated')
    def handle_avatar_updated(data):
        """Diffuser le changement d'avatar à tous les joueurs de la maison"""
        from app import _dbg, get_db_connection
        try:
            user_email = data.get('email')
            if not user_email:
                return

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT house_id, name, avatar, avatar_url, avatar_file FROM users WHERE email=?", (user_email,))
            row = c.fetchone()

            if row and row[0]:
                house_id = row[0]
                room = f"house_{house_id}"

                player_data = {
                    'email': user_email,
                    'name': row[1],
                    'avatar': row[2],
                    'avatar_url': row[3],
                    'avatar_file': row[4]
                }

                conn.close()

                # Diffuser à tous les clients de la room
                emit('player_avatar_update', player_data, room=room)
                _dbg(f'👤 Avatar mis à jour pour {user_email} dans la room {room}')
        except Exception as e:
            _dbg(f'❌ Erreur avatar_updated: {e}')
