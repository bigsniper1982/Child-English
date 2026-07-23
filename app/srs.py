"""Fixed-interval spaced repetition scheduler.

Pure, side-effect-free functions so they can be unit tested in isolation.
A word lives in one of four "boxes". Each box maps to a fixed number of days
until the next review: 1, 3, 7 and 14 days. A correct answer promotes the word
one box (capped at the last box); a wrong answer demotes it so it comes back
sooner.
"""
import datetime as dt

INTERVALS = [1, 3, 7, 14]
MAX_BOX = len(INTERVALS) - 1


def next_box(current_box, correct):
    """Return the box a word moves to after an answer."""
    if correct:
        return min(current_box + 1, MAX_BOX)
    # Wrong answer: drop back so it is reviewed sooner, but never below 0.
    if current_box <= 1:
        return 0
    return 1


def next_review_date(box, today):
    """Return the date a word in ``box`` should next be reviewed."""
    if box < 0:
        raise ValueError("box must be >= 0")
    box = min(box, MAX_BOX)
    return today + dt.timedelta(days=INTERVALS[box])


def schedule(current_box, correct, today):
    """Return ``(new_box, next_review_date)`` after an answer."""
    box = next_box(current_box, correct)
    return box, next_review_date(box, today)


def is_due(review_date, today):
    """A word is due when its review date is today or in the past."""
    if review_date is None:
        return True
    return review_date <= today
