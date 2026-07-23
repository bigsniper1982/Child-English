"""Tests for the controlled theme speaking dialogue engine."""
import pytest

from app.dialogue import (
    SCENARIO,
    get_scenario,
    get_turn,
    num_turns,
    evaluate,
)


def test_scenario_has_between_3_and_5_turns():
    assert 3 <= num_turns() <= 5


def test_turns_cover_expected_topics():
    topics = " ".join(t["question"].lower() for t in SCENARIO["turns"])
    assert "subject" in topics
    assert "after school" in topics or "after-school" in topics
    # a school item is asked about somewhere
    assert any("bring" in t["question"].lower() or "item" in t["question"].lower()
               or "schoolbag" in t["question"].lower() for t in SCENARIO["turns"])


def test_get_turn_returns_prompts_and_keywords():
    turn = get_turn(0)
    assert turn["question"]
    assert turn["sentence_frame"]        # a full-sentence model for the child
    assert isinstance(turn["keywords"], list) and turn["keywords"]


def test_keyword_hit_is_recognised_and_praised():
    turn = get_turn(0)
    kw = turn["keywords"][0]
    result = evaluate(0, f"My favourite subject is {kw}.")
    assert result["hit"] is True
    assert result["advance"] is True
    assert result["stars"] >= 1
    assert result["feedback"]


def test_only_one_correction_is_given_when_answer_is_thin():
    # A single-word answer hits a keyword but should get exactly one gentle nudge.
    turn = get_turn(0)
    kw = turn["keywords"][0]
    result = evaluate(0, kw)
    assert result["hit"] is True
    assert result["corrections"] == 1


def test_off_script_but_safe_answer_is_affirmed_then_redirected():
    result = evaluate(0, "I have a puppy at home.")
    assert result["hit"] is False
    assert result["off_script"] is True
    # affirm first, then bring back to the task
    assert result["feedback"]
    assert result["redirect"] is True


def test_empty_or_unheard_answer_allows_click_to_continue():
    result = evaluate(0, "")
    assert result["hit"] is False
    assert result["allow_skip"] is True


def test_never_claims_official_score():
    turn = get_turn(0)
    kw = turn["keywords"][0]
    result = evaluate(0, f"My favourite subject is {kw}.")
    blob = (result["feedback"] + " " + SCENARIO.get("disclaimer", "")).lower()
    assert "ket" not in blob
    assert "%" not in blob and "score" not in blob


def test_food_theme_has_controlled_cafe_scenario():
    scenario = get_scenario("food_and_drink")
    assert scenario["id"] == "friendly_cafe"
    assert scenario["title"] == "Friendly Café"
    assert 3 <= num_turns("food_and_drink") <= 5
    assert "water" in get_turn(0, "food_and_drink")["keywords"]


@pytest.mark.parametrize(
    ("theme", "scenario_id", "title", "keyword"),
    [
        ("animals_nature", "nature_explorer", "Nature Explorer", "dog"),
        ("family_home", "home_helper", "Home Helper", "mother"),
        ("daily_routines", "day_planner", "My Day Planner", "seven"),
    ],
)
def test_new_themes_have_controlled_speaking_scenarios(
        theme, scenario_id, title, keyword):
    scenario = get_scenario(theme)
    assert scenario["id"] == scenario_id
    assert scenario["title"] == title
    assert 3 <= num_turns(theme) <= 5
    assert keyword in get_turn(0, theme)["keywords"]


def test_food_answer_gets_theme_specific_feedback():
    result = evaluate(0, "I would like some water please.", "food_and_drink")
    assert result["hit"] is True
    assert result["advance"] is True
    assert result["complete_sentence"] is True
    assert result["stars"] == 2


def test_completeness_bonus_for_full_sentence():
    turn = get_turn(0)
    kw = turn["keywords"][0]
    short = evaluate(0, kw)
    full = evaluate(0, f"My favourite subject is {kw}.")
    assert full["stars"] >= short["stars"]
    assert full["complete_sentence"] is True
    assert short["complete_sentence"] is False
