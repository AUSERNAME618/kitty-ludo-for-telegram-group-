"""
persistence.py -- Postgres-backed storage for active Mench games (for
Neon + Render deployment; local disk on Render's free tier is wiped on
every restart, so state must live in an external database).

Needs: pip install psycopg2-binary
Needs env var: DATABASE_URL  (Neon gives you this directly, looks like
  postgres://user:password@host/dbname?sslmode=require)
"""
import os
import json
import pickle
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")


def _connect():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = _connect()
    with conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS games (
                chat_id BIGINT PRIMARY KEY,
                state BYTEA NOT NULL,
                board_message_id BIGINT,
                player_names JSONB NOT NULL,
                player_user_ids JSONB NOT NULL
            )
        """)
    conn.close()


def save_game(chat_id, game, board_message_id, player_names, player_user_ids):
    conn = _connect()
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO games (chat_id, state, board_message_id, player_names, player_user_ids)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET
                state = EXCLUDED.state,
                board_message_id = EXCLUDED.board_message_id,
                player_names = EXCLUDED.player_names,
                player_user_ids = EXCLUDED.player_user_ids
            """,
            (
                chat_id,
                psycopg2.Binary(pickle.dumps(game)),
                board_message_id,
                json.dumps(player_names),
                json.dumps(player_user_ids),
            ),
        )
    conn.close()


def load_game(chat_id):
    conn = _connect()
    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT state, board_message_id, player_names, player_user_ids "
            "FROM games WHERE chat_id = %s",
            (chat_id,),
        )
        row = cur.fetchone()
    conn.close()
    if not row:
        return None
    state, board_message_id, player_names, player_user_ids = row
    return {
        "game": pickle.loads(bytes(state)),
        "board_message_id": board_message_id,
        "player_names": player_names,       # psycopg2 decodes JSONB to dict already
        "player_user_ids": {k: int(v) for k, v in player_user_ids.items()},
    }


def delete_game(chat_id):
    conn = _connect()
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM games WHERE chat_id = %s", (chat_id,))
    conn.close()
