"""Tests for the two mini-game engines (pure logic)."""
import random

from app.games import (
    make_listen_round,
    make_sentence_round,
    make_frog_round,
    grade_listen,
    grade_sentence,
    grade_frog,
    NUM_LISTEN_QUESTIONS,
    NUM_SENTENCE_QUESTIONS,
    NUM_FROG_QUESTIONS,
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


def test_frog_round_has_five_word_finding_jumps():
    rnd = make_frog_round(seed=8)
    assert rnd["game"] == "frog"
    assert len(rnd["questions"]) == NUM_FROG_QUESTIONS == 5
    for q in rnd["questions"]:
        assert q["prompt_zh"] and q["emoji"]
        assert q["answer_id"] in [option["id"] for option in q["options"]]
        assert len(q["options"]) == 4
        assert len({option["id"] for option in q["options"]}) == 4


def test_frog_round_is_theme_scoped_and_deterministic():
    first = make_frog_round(seed=9, theme="animals_nature")
    second = make_frog_round(seed=9, theme="animals_nature")
    assert first == second
    assert all(q["answer_id"].startswith("nature_") for q in first["questions"])
    assert all(option["id"].startswith("nature_")
               for q in first["questions"] for option in q["options"])


def test_grade_frog_counts_only_submitted_correct_first_choices():
    rnd = make_frog_round(seed=10)
    answers = {q["id"]: q["answer_id"] for q in rnd["questions"]}
    wrong = next(option["id"] for option in rnd["questions"][0]["options"]
                 if option["id"] != rnd["questions"][0]["answer_id"])
    answers[rnd["questions"][0]["id"]] = wrong
    score, total = grade_frog(rnd, answers)
    assert score == NUM_FROG_QUESTIONS - 1
    assert total == NUM_FROG_QUESTIONS
