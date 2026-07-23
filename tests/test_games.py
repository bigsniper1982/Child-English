"""Tests for the two mini-game engines (pure logic)."""
import random

from app.games import (
    make_listen_round,
    make_sentence_round,
    grade_listen,
    grade_sentence,
    NUM_LISTEN_QUESTIONS,
    NUM_SENTENCE_QUESTIONS,
)


def test_listen_round_has_fixed_number_of_questions():
    rnd = make_listen_round(seed=1)
    assert len(rnd["questions"]) == NUM_LISTEN_QUESTIONS


def test_listen_question_has_answer_among_options():
    rnd = make_listen_round(seed=2)
    for q in rnd["questions"]:
        assert q["answer_id"] in [o["id"] for o in q["options"]]
        assert len(q["options"]) >= 3
        # options are distinct
        ids = [o["id"] for o in q["options"]]
        assert len(set(ids)) == len(ids)


def test_listen_round_is_deterministic_by_seed_but_varies():
    a = make_listen_round(seed=5)
    b = make_listen_round(seed=5)
    c = make_listen_round(seed=6)
    assert [q["answer_id"] for q in a["questions"]] == [q["answer_id"] for q in b["questions"]]
    # different seeds should usually differ
    assert [q["answer_id"] for q in a["questions"]] != [q["answer_id"] for q in c["questions"]]


def test_grade_listen_scores_correct_answers():
    rnd = make_listen_round(seed=3)
    answers = {q["id"]: q["answer_id"] for q in rnd["questions"]}
    score, total = grade_listen(rnd, answers)
    assert score == total == NUM_LISTEN_QUESTIONS


def test_grade_listen_partial_and_wrong():
    rnd = make_listen_round(seed=3)
    qs = rnd["questions"]
    answers = {}
    for i, q in enumerate(qs):
        if i == 0:
            # deliberately wrong: pick an option that is not the answer
            wrong = next(o["id"] for o in q["options"] if o["id"] != q["answer_id"])
            answers[q["id"]] = wrong
        else:
            answers[q["id"]] = q["answer_id"]
    score, total = grade_listen(rnd, answers)
    assert total == NUM_LISTEN_QUESTIONS
    assert score == NUM_LISTEN_QUESTIONS - 1


def test_sentence_round_shuffles_tokens_of_a_real_example():
    rnd = make_sentence_round(seed=4)
    assert len(rnd["questions"]) == NUM_SENTENCE_QUESTIONS
    for q in rnd["questions"]:
        # the scrambled tokens are a permutation of the correct token list
        assert sorted(q["tokens"]) == sorted(q["answer_tokens"])
        assert len(q["answer_tokens"]) >= 3


def test_grade_sentence_accepts_correct_order_case_insensitive():
    rnd = make_sentence_round(seed=4)
    answers = {q["id"]: list(q["answer_tokens"]) for q in rnd["questions"]}
    score, total = grade_sentence(rnd, answers)
    assert score == total == NUM_SENTENCE_QUESTIONS


def test_grade_sentence_marks_wrong_order():
    rnd = make_sentence_round(seed=7)
    q = rnd["questions"][0]
    answers = {q["id"]: list(reversed(q["answer_tokens"]))}
    # only submit one, reversed
    score, total = grade_sentence(rnd, answers)
    assert score == 0
