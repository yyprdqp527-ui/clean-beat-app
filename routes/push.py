from flask import Blueprint, request, session
import os

push_bp = Blueprint('push', __name__)


@push_bp.route('/api/push/subscribe', methods=['POST'])
def api_push_subscribe():
    """
    Enregistre une subscription push pour l'utilisateur courant.
    Attend un JSON avec: endpoint, keys.p256dh, keys.auth
    """
    from app import _dbg, save_push_subscription
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401

    try:
        subscription_data = request.get_json()

        if not subscription_data or 'endpoint' not in subscription_data:
            return {'success': False, 'error': 'Données invalides'}, 400

        # Ajouter user agent pour debug
        subscription_data['userAgent'] = request.headers.get('User-Agent', '')

        success = save_push_subscription(session['user'], subscription_data)

        if success:
            return {'success': True, 'message': 'Subscription enregistrée'}, 200
        else:
            return {'success': False, 'error': 'Erreur sauvegarde'}, 500

    except Exception as e:
        _dbg(f"❌ Erreur API push subscribe: {e}")
        return {'success': False, 'error': str(e)}, 500


@push_bp.route('/api/push/unsubscribe', methods=['POST'])
def api_push_unsubscribe():
    """
    Désactive une subscription push.
    Attend un JSON avec: endpoint
    """
    from app import _dbg, deactivate_push_subscription
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401

    try:
        data = request.get_json()
        endpoint = data.get('endpoint')

        if not endpoint:
            return {'success': False, 'error': 'Endpoint manquant'}, 400

        success = deactivate_push_subscription(endpoint)

        if success:
            return {'success': True, 'message': 'Subscription désactivée'}, 200
        else:
            return {'success': False, 'error': 'Erreur désactivation'}, 500

    except Exception as e:
        _dbg(f"❌ Erreur API push unsubscribe: {e}")
        return {'success': False, 'error': str(e)}, 500


@push_bp.route('/api/push/vapid-public-key')
def api_push_vapid_key():
    """
    Retourne la clé publique VAPID pour les subscriptions push.
    Supporte les formats normal et base64.
    """
    import base64

    # Essayer d'abord le format base64
    vapid_public_b64 = os.environ.get('VAPID_PUBLIC_KEY_B64', '')

    if vapid_public_b64:
        # Décoder depuis base64
        vapid_public_key = base64.b64decode(vapid_public_b64).decode('utf-8')
    else:
        # Utiliser le format normal
        vapid_public_key = os.environ.get('VAPID_PUBLIC_KEY', '')

    if not vapid_public_key:
        return {'error': 'VAPID key non configurée'}, 500

    return {'publicKey': vapid_public_key}, 200


@push_bp.route('/api/push/test', methods=['POST'])
def api_push_test():
    """
    Route de test pour envoyer une notification push à l'utilisateur courant.
    """
    from app import _dbg, get_user_push_subscriptions, send_push_notification
    if 'user' not in session:
        return {'success': False, 'error': 'Non authentifié'}, 401

    try:
        subscriptions = get_user_push_subscriptions(session['user'])

        if not subscriptions:
            return {'success': False, 'error': 'Aucune subscription trouvée'}, 404

        notification_data = {
            'title': '🧹 Dust Test',
            'body': 'Vos notifications push fonctionnent correctement !',
            'icon': '/static/images/logo.png',
            'url': '/menu'
        }

        sent_count = 0
        for sub in subscriptions:
            if send_push_notification(sub, notification_data):
                sent_count += 1

        if sent_count > 0:
            return {'success': True, 'sent': sent_count}, 200
        else:
            return {'success': False, 'error': 'Échec envoi notifications'}, 500

    except Exception as e:
        _dbg(f"❌ Erreur API push test: {e}")
        return {'success': False, 'error': str(e)}, 500


@push_bp.route('/api/push/status')
def api_push_status():
    """Indique si l'utilisateur courant a une subscription active en DB."""
    from app import get_db_connection
    if 'user' not in session:
        return {'has_subscription': False}, 200
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM push_subscriptions WHERE user_email=? AND is_active=1",
            (session['user'],)
        )
        row = c.fetchone()
        conn.close()
        count = row[0] if row else 0
        return {'has_subscription': count > 0}, 200
    except Exception as e:
        return {'has_subscription': False, 'error': str(e)}, 200
