"""Unit tests for the fixed-interval spaced repetition scheduler (pure functions)."""
import datetime as dt

import pytest

from app.srs import (
    INTERVALS,
    next_box,
    next_review_date,
    schedule,
    is_due,
)

TODAY = dt.date(2026, 7, 23)


def test_intervals_are_the_fixed_schedule():
    assert INTERVALS == [1, 3, 7, 14]


def test_correct_answer_advances_box():
    assert next_box(0, correct=True) == 1
    assert next_box(1, correct=True) == 2
    assert next_box(2, correct=True) == 3


def test_correct_answer_caps_at_last_box():
    assert next_box(3, correct=True) == 3
    assert next_box(99, correct=True) == 3


def test_wrong_answer_brings_word_earlier():
    # A wrong answer must not keep the same or a higher box.
    assert next_box(3, correct=False) < 3
    assert next_box(2, correct=False) == 1
    assert next_box(0, correct=False) == 0


def test_next_review_date_uses_interval_for_box():
    # box 0 -> reviewed today, due in 1 day; box 1 -> due in 3 days; etc.
    assert next_review_date(0, TODAY) == TODAY + dt.timedelta(days=1)
    assert next_review_date(1, TODAY) == TODAY + dt.timedelta(days=3)
    assert next_review_date(2, TODAY) == TODAY + dt.timedelta(days=7)
    assert next_review_date(3, TODAY) == TODAY + dt.timedelta(days=14)


def test_schedule_returns_new_box_and_due_date_on_correct():
    box, due = schedule(current_box=1, correct=True, today=TODAY)
    assert box == 2
    assert due == TODAY + dt.timedelta(days=7)


def test_schedule_brings_earlier_on_wrong():
    box, due = schedule(current_box=3, correct=False, today=TODAY)
    assert box == 1
    # wrong answers must be reviewed sooner than a fresh correct at box 3
    assert due < TODAY + dt.timedelta(days=14)


def test_is_due_boundaries():
    assert is_due(TODAY, TODAY) is True          # due today
    assert is_due(TODAY - dt.timedelta(days=1), TODAY) is True   # overdue
    assert is_due(TODAY + dt.timedelta(days=1), TODAY) is False  # future


def test_is_due_handles_none_as_never_reviewed():
    assert is_due(None, TODAY) is True


def test_negative_box_is_rejected():
    with pytest.raises(ValueError):
        next_review_date(-1, TODAY)
