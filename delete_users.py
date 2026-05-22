"""
Supprime les utilisateurs cibles et toutes leurs données liées.
Usage : DATABASE_URL=postgres://... python delete_users.py
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv()

EMAILS = ['agdaval@yahoo.fr', 'baconjean@hotmail.com']

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL manquant dans les variables d'environnement.")
    sys.exit(1)

# Render fournit parfois "postgres://" mais psycopg2 requiert "postgresql://"
DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print(f"Connexion à la base...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor()

try:
    # ── Identifier les maisons à supprimer ──────────────────────────────────
    # Seulement celles dont TOUS les membres font partie des emails cibles
    cur.execute("""
        SELECT ARRAY_AGG(DISTINCT u.house_id)
        FROM   users u
        WHERE  u.email = ANY(%s)
          AND  u.house_id IS NOT NULL
          AND  NOT EXISTS (
                 SELECT 1 FROM users u2
                 WHERE  u2.house_id = u.house_id
                   AND  u2.email   != ALL(%s)
               )
    """, (EMAILS, EMAILS))
    row = cur.fetchone()
    house_ids = row[0] if row and row[0] else []
    print(f"Emails ciblés  : {EMAILS}")
    print(f"Maisons ciblées: {house_ids}")

    deleted = {}

    # ── ① Données liées directement à l'email ──────────────────────────────
    steps_email = [
        ("baby_tracking_messages",
         "sender_email = ANY(%s) OR recipient_email = ANY(%s)", (EMAILS, EMAILS)),
        ("user_reminders",        "user_email = ANY(%s)",  (EMAILS,)),
        ("proof_requests",
         "requester_email = ANY(%s) OR target_email = ANY(%s)", (EMAILS, EMAILS)),
        ("player_reminders",      "user_email = ANY(%s)",  (EMAILS,)),
        ("beta_feedback",         "user_email = ANY(%s)",  (EMAILS,)),
        ("mystery_rewards",       "user_email = ANY(%s)",  (EMAILS,)),
        ("reward_boxes",          "opened_by  = ANY(%s)",  (EMAILS,)),
        ("user_reminder_settings","user_email = ANY(%s)",  (EMAILS,)),
        ("push_subscriptions",    "user_email = ANY(%s)",  (EMAILS,)),
        ("revealed_gifts",        "revealed_by = ANY(%s)", (EMAILS,)),
        ("message_reads",         "user_email = ANY(%s)",  (EMAILS,)),
        ("messages",
         "sender_email = ANY(%s) OR recipient_email = ANY(%s)", (EMAILS, EMAILS)),
        ("daily_rewards",         "user_email = ANY(%s)",  (EMAILS,)),
        ("comments",              "user_email = ANY(%s)",  (EMAILS,)),
        ("user_rewards",          "user_email = ANY(%s)",  (EMAILS,)),
        ("baby_tracking",         "user_email = ANY(%s)",  (EMAILS,)),
        ("password_reset_tokens", "email       = ANY(%s)", (EMAILS,)),
        ("completed_tasks",       "user_email = ANY(%s)",  (EMAILS,)),
    ]

    for table, condition, params in steps_email:
        cur.execute(f"DELETE FROM {table} WHERE {condition}", params)
        n = cur.rowcount
        if n:
            deleted[table] = deleted.get(table, 0) + n

    # ── ② Données liées à la maison (uniquement les maisons ciblées) ────────
    if house_ids:
        # message_reads doit passer avant messages
        cur.execute("""
            DELETE FROM message_reads
            WHERE message_id IN (SELECT id FROM messages WHERE house_id = ANY(%s))
        """, (house_ids,))
        n = cur.rowcount
        if n:
            deleted['message_reads'] = deleted.get('message_reads', 0) + n

        steps_house = [
            "messages", "proof_requests", "player_reminders", "contests",
            "revealed_gifts", "reward_boxes", "reminders", "baby_tracking",
            "mystery_rewards", "custom_rewards", "task_points_overrides",
            "custom_tasks", "completed_tasks", "custom_rooms",
        ]
        for table in steps_house:
            cur.execute(f"DELETE FROM {table} WHERE house_id = ANY(%s)", (house_ids,))
            n = cur.rowcount
            if n:
                deleted[table] = deleted.get(table, 0) + n

        # Casser la référence circulaire owner_id → users
        cur.execute("UPDATE houses SET owner_id = NULL WHERE id = ANY(%s)", (house_ids,))

    # ── ③ Supprimer les utilisateurs ────────────────────────────────────────
    cur.execute("DELETE FROM users WHERE email = ANY(%s)", (EMAILS,))
    deleted['users'] = cur.rowcount

    # ── ④ Supprimer les maisons devenues vides ──────────────────────────────
    if house_ids:
        cur.execute("DELETE FROM houses WHERE id = ANY(%s)", (house_ids,))
        deleted['houses'] = cur.rowcount

    conn.commit()

    print("\n✅ Suppression réussie !")
    print("Lignes supprimées par table :")
    for table, count in sorted(deleted.items()):
        print(f"  {table:<30} {count}")

except Exception as e:
    conn.rollback()
    print(f"\n❌ Erreur — rollback effectué : {e}")
    raise
finally:
    cur.close()
    conn.close()
