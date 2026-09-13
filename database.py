"""
إدارة قاعدة البيانات - تخزين بيانات اللاعبين باستخدام SQLite
"""
import sqlite3
import time
import json
from contextlib import contextmanager

DB_PATH = "game.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """إنشاء الجداول إذا لم تكن موجودة"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                gold INTEGER DEFAULT 500,
                elixir INTEGER DEFAULT 500,
                last_update REAL,
                town_hall_level INTEGER DEFAULT 1,
                gold_mine_level INTEGER DEFAULT 1,
                elixir_collector_level INTEGER DEFAULT 1,
                army_camp_level INTEGER DEFAULT 1,
                cannon_level INTEGER DEFAULT 1,
                barbarians INTEGER DEFAULT 0,
                archers INTEGER DEFAULT 0,
                trophies INTEGER DEFAULT 0,
                building_queue TEXT DEFAULT NULL,
                training_queue TEXT DEFAULT NULL,
                created_at REAL
            )
        """)


def get_player(user_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def create_player(user_id, username):
    with get_db() as conn:
        now = time.time()
        conn.execute(
            """INSERT OR IGNORE INTO players
               (user_id, username, last_update, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, username, now, now),
        )


def update_player(user_id, **fields):
    """تحديث أي حقول في بيانات اللاعب"""
    if not fields:
        return
    keys = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    with get_db() as conn:
        conn.execute(f"UPDATE players SET {keys} WHERE user_id = ?", values)


def get_all_players(exclude_user_id=None):
    with get_db() as conn:
        if exclude_user_id:
            rows = conn.execute(
                "SELECT * FROM players WHERE user_id != ?", (exclude_user_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM players").fetchall()
        return [dict(r) for r in rows]


def get_leaderboard(limit=10):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT username, trophies FROM players ORDER BY trophies DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
