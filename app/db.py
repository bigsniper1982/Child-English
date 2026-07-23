"""SQLite persistence layer.

A thin wrapper over the standard library ``sqlite3`` module (no ORM). The
connection lives on Flask's application context so it is opened once per
request and closed automatically.
"""
import datetime as dt
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS children (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    fox_stage   INTEGER NOT NULL DEFAULT 0,
    stars       INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_progress (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id     INTEGER NOT NULL,
    word_id      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'learning',   -- learning | known
    box          INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    wrong_count  INTEGER NOT NULL DEFAULT 0,
    next_review  TEXT,
    last_review  TEXT,
    UNIQUE(child_id, word_id)
);

CREATE TABLE IF NOT EXISTS speaking_attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id     INTEGER NOT NULL,
    scenario     TEXT NOT NULL,
    turn_index   INTEGER NOT NULL,
    keyword_hit  INTEGER NOT NULL DEFAULT 0,
    complete     INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
    -- NOTE: raw audio is never stored, only whether a keyword was hit.
);

CREATE TABLE IF NOT EXISTS game_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id     INTEGER NOT NULL,
    game         TEXT NOT NULL,
    score        INTEGER NOT NULL,
    total        INTEGER NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_days (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id     INTEGER NOT NULL,
    day          TEXT NOT NULL,
    UNIQUE(child_id, day)
);
"""

DEFAULT_CHILD_NAME = "英语小探险家"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
        g.db.execute("PRAGMA busy_timeout = 5000")
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and ensure the default child profile exists."""
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()
    ensure_default_child()


def ensure_default_child():
    db = get_db()
    row = db.execute("SELECT id FROM children ORDER BY id LIMIT 1").fetchone()
    if row is None:
        db.execute(
            "INSERT INTO children (name, created_at) VALUES (?, ?)",
            (DEFAULT_CHILD_NAME, dt.date.today().isoformat()),
        )
        db.commit()
        row = db.execute("SELECT id FROM children ORDER BY id LIMIT 1").fetchone()
    return row["id"]


def default_child_id():
    return ensure_default_child()


def get_child(child_id):
    return get_db().execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()


def clear_child_data(child_id):
    """Erase all learning records for a child and reset rewards.

    Also a safety net for any residual temporary audio (none is stored on the
    server, but the parent's 'clear' action documents that intent).
    """
    db = get_db()
    db.execute("DELETE FROM vocab_progress WHERE child_id = ?", (child_id,))
    db.execute("DELETE FROM speaking_attempts WHERE child_id = ?", (child_id,))
    db.execute("DELETE FROM game_results WHERE child_id = ?", (child_id,))
    db.execute("DELETE FROM activity_days WHERE child_id = ?", (child_id,))
    db.execute(
        "UPDATE children SET stars = 0, fox_stage = 0 WHERE id = ?", (child_id,)
    )
    db.commit()


def record_activity_day(child_id, day=None):
    day = day or dt.date.today().isoformat()
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO activity_days (child_id, day) VALUES (?, ?)",
        (child_id, day),
    )
    db.commit()


def add_stars(child_id, n):
    db = get_db()
    db.execute(
        "UPDATE children SET stars = stars + ? WHERE id = ?", (n, child_id)
    )
    # The fox grows one stage for every 20 stars, up to stage 4.
    row = get_child(child_id)
    stage = min(4, row["stars"] // 20)
    db.execute("UPDATE children SET fox_stage = ? WHERE id = ?", (stage, child_id))
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
