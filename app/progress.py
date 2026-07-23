"""Vocabulary progress: ties SRS scheduling to the database."""
import datetime as dt

from app import srs
from app.content import all_word_ids, word_ids
from app.db import get_db, record_activity_day


def _row(child_id, word_id):
    return get_db().execute(
        "SELECT * FROM vocab_progress WHERE child_id = ? AND word_id = ?",
        (child_id, word_id),
    ).fetchone()


def record_review(child_id, word_id, correct, today=None):
    """Record the result of studying/reviewing a word and reschedule it.

    ``correct`` True means the child knew it ("I know this"); False means
    "practise again". Returns the stored row as a dict.
    """
    today = today or dt.date.today()
    db = get_db()
    row = _row(child_id, word_id)
    current_box = row["box"] if row else 0
    new_box, next_review = srs.schedule(current_box, correct, today)
    status = "known" if (correct and new_box >= srs.MAX_BOX) else "learning"

    if row:
        db.execute(
            """UPDATE vocab_progress
                   SET box = ?, status = ?, next_review = ?, last_review = ?,
                       correct_count = correct_count + ?,
                       wrong_count = wrong_count + ?
                 WHERE child_id = ? AND word_id = ?""",
            (new_box, status, next_review.isoformat(), today.isoformat(),
             1 if correct else 0, 0 if correct else 1, child_id, word_id),
        )
    else:
        db.execute(
            """INSERT INTO vocab_progress
                   (child_id, word_id, status, box, correct_count, wrong_count,
                    next_review, last_review)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (child_id, word_id, status, new_box,
             1 if correct else 0, 0 if correct else 1,
             next_review.isoformat(), today.isoformat()),
        )
    db.commit()
    record_activity_day(child_id, today.isoformat())
    return dict(_row(child_id, word_id))


def _ids_for(theme: str | None):
    return all_word_ids() if theme is None else word_ids(theme)


def due_words(child_id, today=None, theme: str | None = None):
    """Due word ids, optionally restricted to one curriculum theme."""
    today = today or dt.date.today()
    allowed = set(_ids_for(theme))
    rows = get_db().execute(
        "SELECT word_id, next_review FROM vocab_progress WHERE child_id = ?",
        (child_id,),
    ).fetchall()
    due = []
    for row in rows:
        if row["word_id"] not in allowed:
            continue
        review = dt.date.fromisoformat(row["next_review"]) if row["next_review"] else None
        if srs.is_due(review, today):
            due.append(row["word_id"])
    return due


def stats(child_id, today=None, theme: str | None = "school_life"):
    """Summary numbers for one theme, or all themes when ``theme`` is None."""
    today = today or dt.date.today()
    db = get_db()
    ids = _ids_for(theme)
    placeholders = ",".join("?" for _ in ids)
    params = (child_id, *ids)
    known = db.execute(
        f"SELECT COUNT(*) c FROM vocab_progress WHERE child_id = ? "
        f"AND status = 'known' AND word_id IN ({placeholders})",
        params,
    ).fetchone()["c"]
    seen = db.execute(
        f"SELECT COUNT(*) c FROM vocab_progress WHERE child_id = ? "
        f"AND word_id IN ({placeholders})",
        params,
    ).fetchone()["c"]
    days = db.execute(
        "SELECT COUNT(*) c FROM activity_days WHERE child_id = ?",
        (child_id,),
    ).fetchone()["c"]
    speaks = db.execute(
        "SELECT COUNT(*) c FROM speaking_attempts WHERE child_id = ?",
        (child_id,),
    ).fetchone()["c"]
    return {
        "total_words": len(ids),
        "seen_words": seen,
        "known_words": known,
        "due_words": len(due_words(child_id, today, theme)),
        "learning_days": days,
        "speaking_attempts": speaks,
    }
