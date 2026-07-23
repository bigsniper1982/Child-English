"""Vocabulary progress: ties SRS scheduling to the database."""
import datetime as dt

from app import srs
from app.content import word_ids
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


def due_words(child_id, today=None):
    """Word ids that are due for review (never-seen words are not 'due')."""
    today = today or dt.date.today()
    rows = get_db().execute(
        "SELECT word_id, next_review FROM vocab_progress WHERE child_id = ?",
        (child_id,),
    ).fetchall()
    due = []
    for r in rows:
        review = dt.date.fromisoformat(r["next_review"]) if r["next_review"] else None
        if srs.is_due(review, today):
            due.append(r["word_id"])
    return due


def stats(child_id, today=None):
    """Summary numbers for the parent dashboard."""
    today = today or dt.date.today()
    db = get_db()
    total_words = len(word_ids())
    known = db.execute(
        "SELECT COUNT(*) c FROM vocab_progress WHERE child_id = ? AND status = 'known'",
        (child_id,),
    ).fetchone()["c"]
    seen = db.execute(
        "SELECT COUNT(*) c FROM vocab_progress WHERE child_id = ?",
        (child_id,),
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
        "total_words": total_words,
        "seen_words": seen,
        "known_words": known,
        "due_words": len(due_words(child_id, today)),
        "learning_days": days,
        "speaking_attempts": speaks,
    }
