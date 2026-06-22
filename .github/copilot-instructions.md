# GitHub Copilot Instructions for CleanBeat

## Project Overview

**CleanBeat** is a gamified household task management web application designed for couples. It motivates users to contribute fairly to household chores through gamification, points, rewards, and real-time synchronization between household members.

## Technology Stack

- **Backend**: Python 3.11, Flask 2.3+, Flask-SocketIO 5.3+
- **Database**: SQLite (development), PostgreSQL (production via Render)
- **Real-time**: WebSocket via Flask-SocketIO + Gevent
- **Frontend**: HTML/CSS/JavaScript (vanilla), Socket.IO client
- **Server**: Gunicorn + Gevent
- **Push Notifications**: pywebpush, py-vapid
- **External Services**: Twilio (SMS), SendGrid (email), DiceBear (avatars)
- **Deployment**: Render platform

## Project Structure

```
clean-beat-app/
├── app.py              # Main Flask application (all routes, DB logic, WebSocket handlers)
├── wsgi.py             # WSGI entry point (gevent monkey patching)
├── gunicorn_config.py  # Gunicorn web server config
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python version (3.11.9)
├── render.yaml         # Render deployment config
├── templates/          # Jinja2 HTML templates (64 files)
│   ├── base.html       # Main layout template
│   ├── login.html      # Authentication pages
│   ├── signup.html
│   ├── menu.html       # Main game menu
│   ├── comments.html   # Messaging/chat between household members
│   └── ...
└── static/             # Frontend assets (JS, CSS, images, audio)
    ├── js/
    ├── css/
    ├── avatars/
    └── ...
```

## Key Application Concepts

### Database Models (SQLite/PostgreSQL)
- **users**: User accounts (email, name, password hash, house_id, avatar, points, registration_step)
- **houses**: Household groups (name, house_name, code, level, health, mood, progress)
- **tasks**: Household tasks (name, room, points value, assignee, status)
- **messages**: In-app messaging between household members
- **baby_tracking**: Baby care event tracking

### Core Features
1. **Multi-player household system**: Users create/join houses with a unique code
2. **Task management**: Assign, complete, validate, and contest household tasks
3. **Points & gamification**: Users earn points for completing tasks
4. **Real-time sync**: WebSocket broadcasts keep all household members in sync
5. **Messaging**: In-app chat between household members (`/comments` route)
6. **Baby tracking**: Track baby care events with timestamps
7. **Push notifications**: Browser push notifications for task updates
8. **PWA**: Progressive Web App with offline support

### Authentication Flow
- Users sign up with email/password (password hashed with werkzeug.security)
- Session-based authentication (Flask sessions)
- Multi-step registration: account creation → profile → house creation/joining

### WebSocket Events
- `join_house`: User joins their household WebSocket room
- `task_validated`: Broadcast when a task is validated
- `points_updated`: Broadcast when player points change
- `new_message`: Broadcast when a new message is sent
- `message_read_update`: Broadcast when a message is read

## Coding Conventions

### Python / Flask
- Route handlers are defined in `app.py` using `@app.route()`
- Database queries use raw SQL with `sqlite3` or `psycopg2`
- Use `session['user_email']` to get the currently logged-in user
- Flash messages use `flash(message, 'success'|'error'|'info')`
- WebSocket events use `@socketio.on('event_name')`

### Templates (Jinja2)
- All templates extend `base.html` or are standalone pages
- Use `{{ url_for('route_name') }}` for URL generation
- Flash messages displayed via `{% with messages = get_flashed_messages(with_categories=true) %}`
- French language is used throughout the UI (the app targets French-speaking users)

### Frontend
- Vanilla JavaScript (no framework)
- Socket.IO for real-time updates
- Mobile-first responsive design
- Glassmorphism design style with gradient backgrounds

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python3 app.py
# App available at http://127.0.0.1:8000

# Key URLs
# /login - User login
# /signup - User registration
# /menu - Main game menu (requires login)
# /invite_partner - Invite household members
# /join_house - Join an existing house
# /comments - Household messaging
```

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection URL (production only)
- `SECRET_KEY`: Flask session secret key
- `TWILIO_*`: Twilio SMS credentials
- `SENDGRID_API_KEY`: SendGrid email credentials
- `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY`: VAPID keys for push notifications (stored in `.vapid_keys.json`)

## Testing
Test scripts are located in the root directory (e.g., `test_websocket_connection.py`, `test_full_cycle.py`). Run them with `python3 <script_name>` while the server is running.
