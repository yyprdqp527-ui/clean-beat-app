from flask import (
    Blueprint, session, request, flash,
    redirect, url_for, jsonify,
    render_template, make_response
)

import json
import random
from datetime import datetime, timedelta

rewards_bp = Blueprint('rewards', __name__)


@rewards_bp.route('/rewards')
def rewards():
    from app import get_db_connection, now_paris, _dbg, check_weekly_reset
    import json
    if 'user' not in session:
        flash("Connecte-toi pour accéder aux récompenses", "warning")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Récupérer la maison de l'utilisateur
        c.execute("SELECT house_id, name FROM users WHERE email=?", (session['user'],))
        user_row = c.fetchone()
        if not user_row or not user_row[0]:
            conn.close()
            flash("Tu dois rejoindre une maison pour accéder aux récompenses", "warning")
            return redirect(url_for('menu') + '?nav=1')
    except Exception as e:
        print(f"❌ Erreur rewards: {e}", flush=True)
        return redirect(url_for('menu') + '?nav=1')
    
    house_id = user_row[0]
    user_name = user_row[1]
    
    # ⚡ Vérifier et effectuer la réinitialisation hebdomadaire des statistiques si nécessaire
    check_weekly_reset(house_id, conn)
    
    # Récupérer le code de la maison
    c.execute("SELECT code FROM houses WHERE id=?", (house_id,))
    house_code = c.fetchone()[0]
    
    # Vérifier si c'est dimanche (gagnant désigné samedi à minuit = dimanche 00:00)
    from datetime import datetime, timedelta
    now = now_paris()
    is_sunday = now.weekday() == 6  # 6 = dimanche
    can_open = is_sunday
    
    # Déterminer le gagnant de la semaine (celui avec le plus de points cette semaine)
    today = now_paris()
    start_of_week = (today - timedelta(days=today.weekday())).date().isoformat()
    
    c.execute("""
        SELECT u.email, u.name, u.is_child_account, COALESCE(SUM(ct.points), 0) as weekly_points
        FROM users u
        LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
            AND DATE(ct.completed_at) >= ?
        WHERE u.house_id = ?
        GROUP BY u.email, u.name, u.is_child_account, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style
        ORDER BY weekly_points DESC
        LIMIT 1
    """, (start_of_week, house_id))
    
    winner_row = c.fetchone()
    is_winner = False
    winner_name = ""
    winner_email = None
    winner_is_child = False
    opening_for_child = False
    
    if winner_row:
        winner_email = winner_row[0]
        winner_name = winner_row[1]
        winner_is_child = bool(winner_row[2])
        if winner_email == session['user']:
            is_winner = True
        elif winner_is_child:
            # 🧒 Le gagnant est un enfant (sans téléphone) — n'importe quel adulte de la maison peut ouvrir à sa place
            try:
                c.execute("SELECT is_child_account FROM users WHERE email=? AND house_id=?", (session['user'], house_id))
                me_row = c.fetchone()
                if me_row and not me_row[0]:
                    is_winner = True
                    opening_for_child = True
            except Exception:
                pass
    
    # Créer la table si elle n'existe pas avec colonne pour la semaine
    c.execute("""
        CREATE TABLE IF NOT EXISTS reward_boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_id INTEGER NOT NULL,
            box_number INTEGER NOT NULL,
            reward_text TEXT NOT NULL,
            opened_by TEXT NOT NULL,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            week_start DATE NOT NULL,
            FOREIGN KEY (house_id) REFERENCES houses(id),
            FOREIGN KEY (opened_by) REFERENCES users(email)
        )
    """)
    
    # Ajouter les colonnes manquantes si elles n'existent pas
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN week_start DATE")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN box_number INTEGER")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN reward_text TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN opened_by TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass
    
    # Vérifier si l'utilisateur a déjà ouvert une case cette semaine
    # (si c'est un parent qui ouvre pour un enfant gagnant, on regarde sur l'email de l'enfant)
    _opened_check_email = winner_email if opening_for_child else session['user']
    c.execute("""
        SELECT box_number, reward_text FROM reward_boxes 
        WHERE house_id=? AND opened_by=? AND week_start=?
    """, (house_id, _opened_check_email, start_of_week))
    user_opened_this_week = c.fetchone()
    already_opened_this_week = user_opened_this_week is not None
    last_reward = user_opened_this_week[1] if user_opened_this_week else ""
    
    # Récupérer toutes les cases ouvertes pour cette maison (historique)
    # TEMPORAIREMENT DÉSACTIVÉ POUR TEST - on renvoie une liste vide
    # c.execute("SELECT box_number FROM reward_boxes WHERE house_id=?", (house_id,))
    # opened_boxes = [row[0] for row in c.fetchall()]
    opened_boxes = []  # Mode test - toutes les cases apparaissent comme non ouvertes
    
    # Récupérer le type de foyer (avec gestion d'erreur si la colonne n'existe pas)
    try:
        c.execute("SELECT house_type FROM houses WHERE id=?", (house_id,))
        house_type_row = c.fetchone()
        house_type = house_type_row[0] if house_type_row and house_type_row[0] else 'family'
    except Exception as e:
        _dbg(f"⚠️ Erreur récupération house_type: {e}")
        house_type = 'family'  # Valeur par défaut
    
    # Créer la table des récompenses personnalisées si elle n'existe pas
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_id INTEGER NOT NULL,
            house_type TEXT NOT NULL,
            rewards_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (house_id) REFERENCES houses(id),
            UNIQUE(house_id, house_type)
        )
    """)
    
    # Ajouter les colonnes manquantes si elles n'existent pas
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN house_type TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN rewards_json TEXT")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass
    
    # Charger les récompenses personnalisées ou utiliser les valeurs par défaut
    c.execute("SELECT rewards_json FROM custom_rewards WHERE house_id=? AND house_type=?", (house_id, 'family'))
    family_custom = c.fetchone()
    
    c.execute("SELECT rewards_json FROM custom_rewards WHERE house_id=? AND house_type=?", (house_id, 'couple'))
    couple_custom = c.fetchone()
    
    c.execute("SELECT rewards_json FROM custom_rewards WHERE house_id=? AND house_type=?", (house_id, 'coloc'))
    coloc_custom = c.fetchone()
    
    conn.close()
    
    # Vérifier si la case a déjà été ouverte cette semaine (valeur réelle)
    # already_opened_this_week est déjà calculé plus haut
    
    # Préparer les trois grilles pour affichage - Récompenses par défaut
    default_rewards_family = [
        'Choisir le menu du dîner',
        'Veiller plus tard le soir',
        'Quelqu\'un sort les poubelles à ta place',
        'Choisir le film du soir',
        'Avoir le droit de sauter le bain',
        'Manger son dessert préféré',
        'Choisir l\'activité du week-end',
        'Recevoir un petit jouet/livre surprise',
        'Avoir du temps d\'écran bonus',
        'Apéro en extérieur à deux',
        'Faire une petite marche nocturne avant de dormir à deux',
        'Soirée jeu de société',
        'Lire une histoire de plus au coucher',
        'Faire des origami avec les parents',
        'Aller au parc/aire de jeux',
        'Choisir la musique en voiture',
        'Faire des crêpes/gaufres ensemble',
        'Dîner au restaurant à deux',
        'Pique-niquer dans le salon',
        'Massage complet',
        'Passer son tour pour ranger sa chambre',
        'Choisir ses vêtements (même bizarres)',
        'Ne pas faire la vaisselle',
        'Ne pas finir ses légumes',
        'Pique-niquer à deux',
        'Grasse matinée sans réveil',
        'Manger le petit-déjeuner au lit',
        'Soirée cinéma à deux',
        'Avoir un goûter spécial',
        'Choisir son petit-déjeuner',
        'Être dispensé de cuisine',
        'Être le chef de famille pour la journée',
        'Commander le repas du soir',
        'Soirée gaming',
        'Avoir un jour oui (parents disent oui à tout le raisonnable)',
        'Avoir du temps solo tranquille',
        'Préparer un gâteau avec maman/papa',
        'Avoir des fleurs',
        'Avoir une journée sans corvées',
        'Soirée pizza',
    ]
    
    default_rewards_couple = [
        'Massage complet',
        'Petit-déjeuner au lit préparé par l\'autre',
        'Faire une petite balade nocturne',
        'Commander le repas du soir',
        'Être dispensé de cuisine',
        'Dîner aux chandelles maison',
        'Soirée cinéma',
        'Grasse matinée sans réveil',
        'Avoir la salle de bain en premier',
        'Soirée gaming',
        'Date night planifiée et payée par l\'autre',
        'Sortie resto',
        'Soirée jeux à deux',
        'Promenade main dans la main',
        'Laisser du temps solo tranquille',
        'Passe retard : pas de reproche si tâche faite plus tard',
        'Avoir des fleurs',
        'Regarder le lever/coucher de soleil ensemble',
        'Pique-niquer à deux',
        'Sortie shopping',
        'Choisir le film/série du soir',
        'Contrôle total de la télécommande',
        'Avoir le côté du lit préféré',
        'Ne pas faire la vaisselle',
        'Être servi son café/thé au réveil',
        'Choisir la musique dans la voiture',
        'Cuisiner ensemble',
        'Dormir sans être réveillé',
        'Journée chic sans pression',
        'Sieste',
        'Commander à manger',
        'Massage sensuel aux huiles',
        'Ne pas cuisiner',
        'Jeu de vérité ou action',
        'Gaming night',
        'Soirée dégustation (vin, fromage, chocolat)',
        'Qu\'on te prépare ton repas préféré',
        'Être dispensé de vaisselle',
        'Ne pas sortir les poubelles',
        'Nuit d\'hôtel ou escapade surprise',
    ]
    
    default_rewards_coloc = [
        'Passer son tour de ménage',
        'Choisir la température de l\'appart',
        'Avoir la salle de bain en premier',
        'Utiliser la machine à laver en priorité',
        'Dispense de sortir les poubelles',
        'Échanger une corvée',
        'Ne pas sortir les poubelles',
        'Être dispensé de vaisselle',
        'Avoir la télécommande TV',
        'Choisir le parfum des produits ménagers',
        'Les autres préparent ton plat préféré',
        'Choisir le fond d\'écran de la TV du salon',
        'Se faire livrer un resto aux frais des autres',
        'Avoir l\'étagère du frigo la plus accessible',
        'Choisir les courses',
        'Passe retard : pas de reproche si tâche faite plus tard',
        'Ne pas cuisiner',
        'Avoir le droit aux meilleurs snacks',
        'Organiser un apéro payé par les colocs',
        'Choisir le resto pour la prochaine sortie groupe',
        'Monopoliser le salon pour une soirée',
        'Mettre sa musique à fond',
        'Organiser une soirée avec ses amis',
        'Avoir la paix absolue',
        'Voter pour le prochain achat commun',
        'Utiliser l\'espace commun pour son hobby',
        'Avoir le meilleur siège du salon',
        'Soirée pizza',
        'Occuper la cuisine pour un projet culinaire',
        'Repas à thème (mexicain, italien…)',
        'Obliger les colocs à faire une soirée jeux',
        'Tournoi jeu de cartes',
        'Choisir le film de la soirée coloc',
        'Gaming night',
        'Temps solo dans les espaces communs',
        'Journée full chill',
        'Les colocs doivent porter un accessoire ridicule toute la soirée',
        'Accès prioritaire aux équipements (TV, console…)',
        'Tes colocs organisent un brunch',
        'Quelqu\'un sort les poubelles à ta place',
    ]
    
    # Utiliser les récompenses personnalisées si elles existent, sinon les valeurs par défaut
    try:
        rewards_family_list = json.loads(family_custom[0]) if family_custom else default_rewards_family
    except Exception as e:
        _dbg(f"⚠️ Erreur parsing JSON family rewards: {e}")
        rewards_family_list = default_rewards_family
    
    try:
        rewards_couple_list = json.loads(couple_custom[0]) if couple_custom else default_rewards_couple
    except Exception as e:
        _dbg(f"⚠️ Erreur parsing JSON couple rewards: {e}")
        rewards_couple_list = default_rewards_couple
    
    try:
        rewards_coloc_list = json.loads(coloc_custom[0]) if coloc_custom else default_rewards_coloc
    except Exception as e:
        _dbg(f"⚠️ Erreur parsing JSON coloc rewards: {e}")
        rewards_coloc_list = default_rewards_coloc

    try:
        response = make_response(render_template('rewards.html', 
                             house_code=house_code, 
                             is_winner=is_winner,
                             winner_name=winner_name,
                             winner_is_child=winner_is_child,
                             opening_for_child=opening_for_child,
                             user_name=user_name,
                             opened_boxes=opened_boxes,
                             can_open=can_open,
                             already_opened_this_week=already_opened_this_week,
                             last_reward=last_reward,
                             email=session['user'],
                             rewards_family=rewards_family_list,
                             rewards_couple=rewards_couple_list,
                             rewards_coloc=rewards_coloc_list,
                             house_type=house_type))
        
        # Empêcher la mise en cache
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    except Exception as e:
        _dbg(f"❌ Erreur dans /rewards: {e}")
        import traceback
        traceback.print_exc()
        flash("Une erreur s'est produite lors du chargement de la grille", "danger")
        return redirect(url_for('menu') + '?nav=1')


@rewards_bp.route('/update_rewards', methods=['POST'])
def update_rewards():
    from app import get_db_connection
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'}), 401
    
    data = request.get_json()
    house_type = data.get('house_type')
    rewards = data.get('rewards')
    
    if not house_type or not rewards:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400
    
    if not isinstance(rewards, list) or len(rewards) != 40:
        return jsonify({'success': False, 'message': 'Il faut exactement 40 récompenses'}), 400
    
    # Valider que toutes les récompenses sont des chaînes non vides
    for reward in rewards:
        if not isinstance(reward, str) or not reward.strip():
            return jsonify({'success': False, 'message': 'Toutes les récompenses doivent être remplies'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'message': 'Pas de maison'}), 400
    
    house_id = user_row[0]
    
    # Sauvegarder les récompenses personnalisées
    rewards_json = json.dumps(rewards, ensure_ascii=False)
    
    try:
        c.execute("""
            INSERT INTO custom_rewards (house_id, house_type, rewards_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(house_id, house_type) 
            DO UPDATE SET rewards_json=?, updated_at=CURRENT_TIMESTAMP
        """, (house_id, house_type, rewards_json, rewards_json))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Récompenses sauvegardées'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500


@rewards_bp.route('/open_reward_box', methods=['POST'])
def open_reward_box():
    from app import get_db_connection, now_paris, _dbg
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'}), 401
    
    box_number = request.json.get('box_number')
    
    if not box_number or not isinstance(box_number, int) or box_number < 1 or box_number > 40:
        return jsonify({'success': False, 'message': 'Numéro de case invalide'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    user_row = c.fetchone()
    if not user_row or not user_row[0]:
        conn.close()
        return jsonify({'success': False, 'message': 'Pas de maison'}), 400
    
    house_id = user_row[0]
    
    # Vérifier si c'est dimanche après 6h du matin
    from datetime import datetime, timedelta
    now = now_paris()
    is_sunday = now.weekday() == 6
    is_after_6am = now.hour >= 6
    if not (is_sunday and is_after_6am):
        conn.close()
        return jsonify({'success': False, 'message': 'La grille cadeau mystère est disponible uniquement le dimanche à partir de 6h !'}), 403
    
    # Calculer le début de la semaine
    today = now_paris()
    start_of_week = (today - timedelta(days=today.weekday())).date().isoformat()
    
    # Vérifier que l'utilisateur est le gagnant de la semaine
    # (ou — cas spécial — un parent ouvrant pour un enfant gagnant sans téléphone)
    c.execute("""
        SELECT u.email, u.is_child_account, COALESCE(SUM(ct.points), 0) as weekly_points
        FROM users u
        LEFT JOIN completed_tasks ct ON u.email = ct.user_email 
            AND DATE(ct.completed_at) >= ?
        WHERE u.house_id = ?
        GROUP BY u.email, u.name, u.is_child_account, u.avatar, u.avatar_file, u.avatar_url, u.avatar_style
        ORDER BY weekly_points DESC
        LIMIT 1
    """, (start_of_week, house_id))
    
    winner_row = c.fetchone()
    if not winner_row:
        conn.close()
        return jsonify({'success': False, 'message': 'Aucun gagnant cette semaine'}), 403

    _winner_email = winner_row[0]
    _winner_is_child = bool(winner_row[1])
    opening_for_child = False

    if _winner_email == session['user']:
        # Le user est lui-même le gagnant
        opener_email = session['user']
    elif _winner_is_child:
        # Le gagnant est un enfant : autoriser tout adulte de la maison à ouvrir à sa place
        c.execute("SELECT is_child_account FROM users WHERE email=? AND house_id=?", (session['user'], house_id))
        me_row = c.fetchone()
        if not me_row or me_row[0]:
            conn.close()
            return jsonify({'success': False, 'message': 'Seul le gagnant de la semaine peut ouvrir une case'}), 403
        opener_email = _winner_email  # on enregistre la box au nom de l'enfant
        opening_for_child = True
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'Seul le gagnant de la semaine peut ouvrir une case'}), 403
    
    # Créer les tables si elles n'existent pas (AVANT tout SELECT dessus)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reward_boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_id INTEGER NOT NULL,
            box_number INTEGER NOT NULL,
            reward_text TEXT NOT NULL,
            opened_by TEXT NOT NULL,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            week_start DATE NOT NULL,
            FOREIGN KEY (house_id) REFERENCES houses(id),
            FOREIGN KEY (opened_by) REFERENCES users(email)
        )
    """)
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN week_start DATE")
    except:
        pass
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN box_number INTEGER")
    except:
        pass
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN reward_text TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN opened_by TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE reward_boxes ADD COLUMN opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_id INTEGER NOT NULL,
            house_type TEXT NOT NULL,
            rewards_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (house_id) REFERENCES houses(id),
            UNIQUE(house_id, house_type)
        )
    """)
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN house_type TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN rewards_json TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE custom_rewards ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass

    c.execute("SELECT box_number FROM reward_boxes WHERE house_id=? AND opened_by=? AND week_start=?", 
              (house_id, opener_email, start_of_week))
    if c.fetchone():
        conn.close()
        msg = ('Le cadeau de cette semaine a déjà été ouvert pour cet enfant !'
               if opening_for_child else
               'Tu as déjà ouvert ton cadeau mystère cette semaine !')
        return jsonify({'success': False, 'message': msg}), 400
    
    # === GRILLES DE RÉCOMPENSES PAR TYPE DE FOYER ===
    
    # Récupérer le type de foyer de la maison pour choisir la bonne grille
    c.execute("SELECT house_type FROM houses WHERE id=?", (house_id,))
    house_type_row = c.fetchone()
    house_type = house_type_row[0] if house_type_row and house_type_row[0] else 'family'
    
    _dbg(f"[DEBUG open_reward_box] house_id={house_id}, house_type={house_type}, box_number={box_number}")
    
    # Charger les récompenses personnalisées ou les récompenses par défaut
    # Grille Parents/Enfants (40 récompenses par défaut)
    default_rewards_family = [
        {"text": "Choisir le menu du dîner", "image": None},
        {"text": "Veiller plus tard le soir", "image": None},
        {"text": "Quelqu'un sort les poubelles à ta place", "image": None},
        {"text": "Choisir le film du soir", "image": None},
        {"text": "Avoir le droit de sauter le bain", "image": None},
        {"text": "Manger son dessert préféré", "image": None},
        {"text": "Choisir l'activité du week-end", "image": None},
        {"text": "Recevoir un petit jouet/livre surprise", "image": None},
        {"text": "Avoir du temps d'écran bonus", "image": None},
        {"text": "Apéro en extérieur à deux", "image": None},
        {"text": "Faire une petite marche nocturne avant de dormir à deux", "image": None},
        {"text": "Soirée jeu de société", "image": None},
        {"text": "Lire une histoire de plus au coucher", "image": None},
        {"text": "Faire des origami avec les parents", "image": None},
        {"text": "Aller au parc/aire de jeux", "image": None},
        {"text": "Choisir la musique en voiture", "image": None},
        {"text": "Faire des crêpes/gaufres ensemble", "image": None},
        {"text": "Dîner au restaurant à deux", "image": None},
        {"text": "Pique-niquer dans le salon", "image": None},
        {"text": "Massage complet", "image": None},
        {"text": "Passer son tour pour ranger sa chambre", "image": None},
        {"text": "Choisir ses vêtements (même bizarres)", "image": None},
        {"text": "Ne pas faire la vaisselle", "image": None},
        {"text": "Ne pas finir ses légumes", "image": None},
        {"text": "Pique-niquer à deux", "image": None},
        {"text": "Grasse matinée sans réveil", "image": None},
        {"text": "Manger le petit-déjeuner au lit", "image": None},
        {"text": "Soirée cinéma à deux", "image": None},
        {"text": "Avoir un goûter spécial", "image": None},
        {"text": "Choisir son petit-déjeuner", "image": None},
        {"text": "Être dispensé de cuisine", "image": None},
        {"text": "Être le 'chef de famille' pour la journée", "image": None},
        {"text": "Commander le repas du soir", "image": None},
        {"text": "Soirée gaming (dans la limite du raisonnable)", "image": None},
        {"text": "Avoir un jour 'oui' (parents disent oui à tout le raisonnable)", "image": None},
        {"text": "Avoir du temps solo tranquille", "image": None},
        {"text": "Préparer un gâteau avec maman/papa", "image": None},
        {"text": "Avoir des fleurs", "image": None},
        {"text": "Avoir une journée sans corvées", "image": None},
        {"text": "Soirée pizza", "image": None},
    ]
    
    # Grille Couple (40 récompenses par défaut)
    default_rewards_couple = [
        {"text": "Massage complet", "image": None},
        {"text": "Petit-déjeuner au lit préparé par l'autre", "image": None},
        {"text": "Faire une petite balade nocturne", "image": None},
        {"text": "Commander le repas du soir", "image": None},
        {"text": "Être dispensé de cuisine", "image": None},
        {"text": "Dîner aux chandelles maison", "image": None},
        {"text": "Soirée cinéma", "image": None},
        {"text": "Grasse matinée sans réveil", "image": None},
        {"text": "Avoir la salle de bain en premier", "image": None},
        {"text": "Soirée gaming", "image": None},
        {"text": "Date night planifiée et payée par l'autre", "image": None},
        {"text": "Sortie resto", "image": None},
        {"text": "Soirée jeux à deux", "image": None},
        {"text": "Promenade main dans la main", "image": None},
        {"text": "Laisser du temps solo tranquille", "image": None},
        {"text": "« Passe retard » pas de reproche si tâche faite plus tard", "image": None},
        {"text": "Avoir des fleurs", "image": None},
        {"text": "Regarder le lever/coucher de soleil ensemble", "image": None},
        {"text": "Pique-niquer à deux", "image": None},
        {"text": "Sortie shopping", "image": None},
        {"text": "Choisir le film/série du soir", "image": None},
        {"text": "Contrôle total de la télécommande", "image": None},
        {"text": "Avoir le côté du lit préféré", "image": None},
        {"text": "Ne pas faire la vaisselle", "image": None},
        {"text": "Être servi son café/thé au réveil", "image": None},
        {"text": "Choisir la musique dans la voiture", "image": None},
        {"text": "Cuisiner ensemble", "image": None},
        {"text": "Dormir sans être réveillé", "image": None},
        {"text": "Journée chic sans pression", "image": None},
        {"text": "Sieste", "image": None},
        {"text": "Commander à manger", "image": None},
        {"text": "Massage sensuel aux huiles", "image": None},
        {"text": "Ne pas cuisiner", "image": None},
        {"text": "Jeu de vérité ou action", "image": None},
        {"text": "Gaming night", "image": None},
        {"text": "Soirée dégustation (vin, fromage, chocolat)", "image": None},
        {"text": "Qu'on te prépare ton repas préféré", "image": None},
        {"text": "Être dispensé de vaisselle", "image": None},
        {"text": "Ne pas sortir les poubelles", "image": None},
        {"text": "Nuit d'hôtel ou escapade surprise", "image": None},
    ]
    
    # Grille Coloc (40 récompenses par défaut)
    default_rewards_coloc = [
        {"text": "Passer son tour de ménage", "image": None},
        {"text": "Choisir la température de l'appart", "image": None},
        {"text": "Avoir la salle de bain en premier", "image": None},
        {"text": "Utiliser la machine à laver en priorité", "image": None},
        {"text": "Dispense de sortir les poubelles", "image": None},
        {"text": "Échanger une corvée", "image": None},
        {"text": "Ne pas sortir les poubelles", "image": None},
        {"text": "Être dispensé de vaisselle", "image": None},
        {"text": "Avoir la télécommande TV", "image": None},
        {"text": "Choisir le parfum des produits ménagers", "image": None},
        {"text": "Les autres préparent ton plat préféré", "image": None},
        {"text": "Choisis ta récompense", "image": None},
        {"text": "Se faire livrer un resto aux frais des autres", "image": None},
        {"text": "Avoir l'étagère du frigo la plus accessible", "image": None},
        {"text": "Choisir les courses", "image": None},
        {"text": "« Passe retard » pas de reproche si tâche faite plus tard", "image": None},
        {"text": "Ne pas cuisiner", "image": None},
        {"text": "Avoir le droit aux meilleurs snacks", "image": None},
        {"text": "Organiser un apéro payé par les colocs", "image": None},
        {"text": "Choisir le resto pour la prochaine sortie groupe", "image": None},
        {"text": "Monopoliser le salon pour une soirée", "image": None},
        {"text": "Mettre sa musique à fond", "image": None},
        {"text": "Organiser une soirée avec ses amis", "image": None},
        {"text": "Avoir la paix absolue", "image": None},
        {"text": "Échanger une corvée", "image": None},
        {"text": "Utiliser l'espace commun pour son hobby", "image": None},
        {"text": "Avoir le meilleur siège du salon", "image": None},
        {"text": "Soirée pizza", "image": None},
        {"text": "Occuper la cuisine pour un projet culinaire", "image": None},
        {"text": "Repas à thème (mexicain, italien...)", "image": None},
        {"text": "Obliger les colocs à faire une soirée jeux", "image": None},
        {"text": "Tournoi jeu de cartes", "image": None},
        {"text": "Choisir le film de la soirée coloc", "image": None},
        {"text": "Gaming night", "image": None},
        {"text": "Temps solo dans les espaces communs", "image": None},
        {"text": "Journée « full chill »", "image": None},
        {"text": "Les colocs doivent porter un accessoire ridicule toute la soirée", "image": None},
        {"text": "Accès prioritaire aux équipements (TV, console...)", "image": None},
        {"text": "Tes colocs organisent un brunch", "image": None},
        {"text": "Quelqu'un sort les poubelles à ta place", "image": None},
    ]
    
    # Charger les récompenses personnalisées si elles existent
    c.execute("SELECT rewards_json FROM custom_rewards WHERE house_id=? AND house_type=?", (house_id, house_type))
    custom_rewards_row = c.fetchone()
    
    _dbg(f"[DEBUG] Recherche custom_rewards: house_id={house_id}, house_type={house_type}")
    _dbg(f"[DEBUG] custom_rewards_row trouvé: {custom_rewards_row is not None}")
    
    if custom_rewards_row:
        # Utiliser les récompenses personnalisées
        custom_rewards_list = json.loads(custom_rewards_row[0])
        rewards = [{"text": reward, "image": None} for reward in custom_rewards_list]
        _dbg(f"[DEBUG] Utilisation de {len(rewards)} récompenses personnalisées")
    else:
        # Utiliser les récompenses par défaut selon le type de foyer
        if house_type == 'couple':
            rewards = default_rewards_couple
            _dbg(f"[DEBUG] Utilisation des récompenses par défaut COUPLE")
        elif house_type == 'coloc':
            rewards = default_rewards_coloc
            _dbg(f"[DEBUG] Utilisation des récompenses par défaut COLOC")
        else:
            rewards = default_rewards_family
            _dbg(f"[DEBUG] Utilisation des récompenses par défaut FAMILLE")
    
    reward = random.choice(rewards)
    reward_text = reward["text"]
    reward_image = reward["image"]
    
    # S'assurer que la table mystery_rewards existe
    c.execute("""
    CREATE TABLE IF NOT EXISTS mystery_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        house_id INTEGER NOT NULL,
        reward_text TEXT NOT NULL,
        won_date DATE DEFAULT CURRENT_DATE,
        used INTEGER DEFAULT 0,
        used_date DATE,
        FOREIGN KEY(user_email) REFERENCES users(email),
        FOREIGN KEY(house_id) REFERENCES houses(id)
    )
    """)
    
    # Enregistrer la case ouverte avec la semaine
    # MODE TEST: On supprime d'abord l'ancienne entrée si elle existe
    try:
        c.execute("DELETE FROM reward_boxes WHERE house_id=? AND box_number=?", (house_id, box_number))
    except:
        pass
    
    try:
        c.execute("""
            INSERT INTO reward_boxes (house_id, box_number, reward_text, opened_by, week_start)
            VALUES (?, ?, ?, ?, ?)
        """, (house_id, box_number, reward_text, opener_email, start_of_week))
        
        # Enregistrer la récompense dans les récompenses du joueur (l'enfant si parent ouvre pour lui)
        _dbg(f"[DEBUG] Insertion dans mystery_rewards: user={opener_email}, house={house_id}, reward={reward_text}, opening_for_child={opening_for_child}")
        c.execute("""
            INSERT INTO mystery_rewards (user_email, house_id, reward_text, won_date, used)
            VALUES (?, ?, ?, date('now'), 0)
        """, (opener_email, house_id, reward_text))
        
        conn.commit()
        _dbg(f"[DEBUG] Récompense enregistrée avec succès!")
    except Exception as e:
        conn.close()
        _dbg(f"[ERROR] Erreur lors de l'insertion: {str(e)}")
        return jsonify({'success': False, 'message': f'Erreur base de données: {str(e)}'}), 500
    
    conn.close()
    
    # Récupérer le nom de l'utilisateur
    user_name = session.get('user_name', '')
    if not user_name:
        conn2 = get_db_connection()
        c2 = conn2.cursor()
        c2.execute("SELECT name FROM users WHERE email=?", (session['user'],))
        name_row = c2.fetchone()
        user_name = name_row[0] if name_row and name_row[0] else 'Champion'
        conn2.close()
    
    response = {'success': True, 'reward': reward_text, 'winner_name': user_name}
    if reward_image:
        response['image'] = reward_image
    
    return jsonify(response)


@rewards_bp.route('/mes_recompenses')
def mes_recompenses():
    """Page pour voir les récompenses mystère de tous les joueurs de la maison"""
    from app import get_db_connection, _dbg, get_house_players_points
    if 'user' not in session:
        flash("Connectez-vous d'abord", "warning")
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer la maison de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_row = c.fetchone()
    if not house_row or not house_row[0]:
        conn.close()
        flash("Vous devez rejoindre une maison", "warning")
        return redirect(url_for('menu') + '?nav=1')
    
    house_id = house_row[0]
    
    _dbg(f"[DEBUG mes_recompenses] house_id={house_id}, user={session['user']}")
    
    # ===== UTILISER get_house_players_points() pour garantir les mêmes avatars que le menu =====
    players_from_menu = get_house_players_points(house_id)
    
    # Construire directement la liste players_data depuis get_house_players_points
    players_data = []
    for p in players_from_menu:
        player_email = p.get('email')
        player_name = p.get('name', '')
        
        # Récompenses disponibles de ce joueur
        c.execute("""
            SELECT id, reward_text, won_date
            FROM mystery_rewards
            WHERE user_email=? AND used=0
            ORDER BY id DESC
        """, (player_email,))
        
        available = []
        for r in c.fetchall():
            available.append({
                'id': r[0],
                'text': r[1],
                'date': r[2]
            })
        
        _dbg(f"[DEBUG] Joueur {player_name} ({player_email}): {len(available)} récompenses disponibles")
        _dbg(f"[DEBUG]   avatar={p.get('avatar')}, file={p.get('avatar_file')}, url={p.get('avatar_url')}, style={p.get('avatar_style')}")
        
        # Récompenses utilisées de ce joueur
        c.execute("""
            SELECT id, reward_text, won_date, used_date
            FROM mystery_rewards
            WHERE user_email=? AND used=1
            ORDER BY used_date DESC
        """, (player_email,))
        
        used = []
        for r in c.fetchall():
            used.append({
                'id': r[0],
                'text': r[1],
                'won_date': r[2],
                'used_date': r[3]
            })
        
        players_data.append({
            'email': player_email,
            'name': player_name,
            'avatar': p.get('avatar'),
            'avatar_file': p.get('avatar_file'),
            'avatar_url': p.get('avatar_url'),
            'avatar_style': p.get('avatar_style', 'adventurer'),
            'available_rewards': available,
            'used_rewards': used,
            'is_current_user': player_email == session['user']
        })
    
    conn.close()
    
    response = make_response(render_template('rewards_grid.html',
                         players=players_data,
                         current_user=session['user'],
                         hide_header=True))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@rewards_bp.route('/use_reward/<int:reward_id>', methods=['POST'])
def use_reward(reward_id):
    """Marquer une récompense comme utilisée"""
    from app import get_db_connection, _dbg
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'}), 401
    
    _dbg(f"[DEBUG use_reward] reward_id={reward_id}, user={session['user']}")
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Vérifier que la récompense appartient à l'utilisateur
        c.execute("""
            SELECT id FROM mystery_rewards
            WHERE id=? AND user_email=? AND used=0
        """, (reward_id, session['user']))
        
        reward_row = c.fetchone()
        _dbg(f"[DEBUG] Récompense trouvée: {reward_row is not None}")
        
        if not reward_row:
            conn.close()
            return jsonify({'success': False, 'message': 'Récompense non trouvée'}), 404
        
        # Marquer comme utilisée
        c.execute("""
            UPDATE mystery_rewards
            SET used=1, used_date=date('now')
            WHERE id=?
        """, (reward_id,))
        
        rows_affected = c.rowcount
        _dbg(f"[DEBUG] Lignes modifiées: {rows_affected}")
        
        conn.commit()
        conn.close()
        
        _dbg(f"[DEBUG] Récompense {reward_id} marquée comme utilisée avec succès")
        
        return jsonify({'success': True})
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': 'Une erreur est survenue, réessaie.'}), 500


@rewards_bp.route('/buy_reward/<int:reward_id>')
def buy_reward(reward_id):
    from app import get_db_connection, now_paris
    # Fonctionnalité temporairement désactivée
    return redirect(url_for('menu') + '?nav=1')
    
    if 'user' not in session:
        flash("Connecte-toi pour acheter une récompense", "warning")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    c = conn.cursor()

    # Vérifier les points et si l'utilisateur a déjà acheté la récompense aujourd'hui
    c.execute("SELECT points FROM users WHERE email=?", (session['user'],))
    points = c.fetchone()[0]

    c.execute("SELECT cost FROM rewards WHERE id=?", (reward_id,))
    cost = c.fetchone()[0]

    today = now_paris().date().isoformat()
    c.execute("SELECT * FROM user_rewards WHERE user_email=? AND reward_id=? AND purchased_date=?", (session['user'], reward_id, today))
    already_bought_today = c.fetchone()

    if already_bought_today:
        flash("Tu as déjà obtenu cette récompense aujourd'hui. Reviens demain !", "info")
    elif points < cost:
        flash("Pas assez de points pour acheter cette récompense.", "danger")
    else:
        # Déduire les points et ajouter la récompense avec la date d'aujourd'hui
        c.execute("UPDATE users SET points = points - ? WHERE email=?", (cost, session['user']))
        c.execute("INSERT INTO user_rewards (user_email, reward_id, purchased_date) VALUES (?, ?, ?)", (session['user'], reward_id, today))
        conn.commit()
        flash("Récompense achetée !", "success")

    conn.close()
    return redirect(url_for('rewards.rewards'))


# ===============================
# NOUVELLES ROUTES CLEANBEAT
# ===============================

@rewards_bp.route('/gifts')
def gifts():
    """Grille de cadeaux Dust - débloquée le dimanche matin"""
    from app import get_db_connection, now_paris, check_weekly_reset, get_house_players_points
    if 'user' not in session:
        flash("🔐 Connecte-toi pour voir tes cadeaux !", "warning")
        return redirect(url_for('auth.signup_email'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer house_id de l'utilisateur
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_id = c.fetchone()[0]
    
    # ⚡ Vérifier et effectuer la réinitialisation hebdomadaire des statistiques si nécessaire
    check_weekly_reset(house_id, conn)
    
    # Récupérer les informations de la maison (utilise 'house_name' si présent, sinon 'name')
    c.execute("SELECT code, name, house_name FROM houses WHERE id=?", (house_id,))
    house_info = c.fetchone()
    house_code = house_info[0]
    # colonne 2 = house_name, colonne 1 = name
    house_name = house_info[2] if house_info and house_info[2] else (house_info[1] if house_info and house_info[1] else None)
    
    # Récupérer tous les joueurs
    players = get_house_players_points(house_id)
    
    # Vérifier si c'est dimanche (accessible dès samedi minuit = dimanche 00:00)
    from datetime import datetime
    now = now_paris()
    is_sunday = now.weekday() == 6  # 6 = dimanche
    can_open_gifts = is_sunday
    
    # Liste des cadeaux prédéfinis
    default_gifts = [
        {'id': 1, 'name': '🍽️ Dîner au restaurant', 'revealed': False, 'description': 'Une soirée romantique au restaurant de votre choix !'},
        {'id': 2, 'name': '💆 Massage 30 min', 'revealed': False, 'description': 'Un moment de détente bien mérité !'},
        {'id': 3, 'name': '💐 Bouquet de fleurs', 'revealed': False, 'description': 'De jolies fleurs pour égayer la maison !'},
        {'id': 4, 'name': '📺 Choisir la série', 'revealed': False, 'description': 'Le pouvoir de choisir ce qu\'on regarde ce soir !'},
        {'id': 5, 'name': '🛏️ Petit déj au lit', 'revealed': False, 'description': 'Un réveil en douceur le dimanche matin !'},
        {'id': 6, 'name': '🧖‍♀️ Journée spa', 'revealed': False, 'description': 'Une journée complète de relaxation !'},
        {'id': 7, 'name': '🎬 Sortie cinéma', 'revealed': False, 'description': 'Une soirée ciné avec pop-corn !'},
        {'id': 8, 'name': '🏖️ Week-end surprise', 'revealed': False, 'description': 'Une escapade mystère de 2 jours !'},
        {'id': 9, 'name': '🕯️ Dîner aux chandelles', 'revealed': False, 'description': 'Un repas romantique à la maison !'}
    ]
    
    # Récupérer les cadeaux révélés depuis la base de données
    c.execute("SELECT gift_id, revealed_by, revealed_date FROM revealed_gifts WHERE house_id=?", (house_id,))
    revealed_data = {row[0]: {'revealed_by': row[1], 'revealed_date': row[2]} for row in c.fetchall()}
    
    # Mettre à jour les cadeaux avec les données révélées
    for gift in default_gifts:
        if gift['id'] in revealed_data:
            gift['revealed'] = True
            gift['revealed_by'] = revealed_data[gift['id']]['revealed_by']
            gift['revealed_date'] = revealed_data[gift['id']]['revealed_date']
    
    conn.close()
    
    return render_template('gifts.html', 
                         gifts=default_gifts, 
                         can_open_gifts=can_open_gifts,
                         players=players, 
                         house_code=house_code,
                         house_name=house_name)

@rewards_bp.route('/reveal_gift/<int:gift_id>')
def reveal_gift(gift_id):
    """Révéler un cadeau"""
    from app import get_db_connection, now_paris
    if 'user' not in session:
        return redirect(url_for('auth.signup_email'))
    
    # Vérifier si c'est dimanche (accessible dès samedi minuit = dimanche 00:00)
    from datetime import datetime
    now = now_paris()
    is_sunday = now.weekday() == 6
    can_open_gifts = is_sunday
    
    if not can_open_gifts:
        flash("🚫 Les cadeaux ne sont disponibles que le dimanche ! 🎁", "warning")
        return redirect(url_for('rewards.gifts'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Récupérer house_id
    c.execute("SELECT house_id FROM users WHERE email=?", (session['user'],))
    house_id = c.fetchone()[0]
    
    # Vérifier si le cadeau n'est pas déjà révélé
    c.execute("SELECT * FROM revealed_gifts WHERE house_id=? AND gift_id=?", (house_id, gift_id))
    if c.fetchone():
        flash("🎁 Ce cadeau a déjà été ouvert ! Choisissez-en un autre ! ✨", "info")
        conn.close()
        return redirect(url_for('rewards.gifts'))
    
    # Révéler le cadeau
    current_date = now_paris().isoformat()
    c.execute("INSERT INTO revealed_gifts (house_id, gift_id, revealed_by, revealed_date) VALUES (?, ?, ?, ?)", 
              (house_id, gift_id, session['user'], current_date))
    conn.commit()
    conn.close()
    
    # Messages de félicitations
    gift_names = {
        1: '🍽️ Dîner au restaurant',
        2: '💆 Massage 30 min', 
        3: '💐 Bouquet de fleurs',
        4: '📺 Choisir la série',
        5: '🛏️ Petit déj au lit',
        6: '🧖‍♀️ Journée spa',
        7: '🎬 Sortie cinéma',
        8: '🏖️ Week-end surprise',
        9: '🕯️ Dîner aux chandelles'
    }
    
    gift_name = gift_names.get(gift_id, 'Cadeau mystère')
    flash(f"🎊 FÉLICITATIONS ! Vous avez gagné : {gift_name} ! 🎉 Profitez bien ! ✨", "success")
    
    return redirect(url_for('rewards.gifts'))
