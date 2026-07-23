"""Schema-validation tests for every vocabulary theme."""
import re
import pytest

from app.content import load_words, list_themes, get_theme, ALLOWED_POS

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
REQUIRED = ("id", "en", "zh", "pos", "emoji", "color", "chunk", "example")


def test_five_original_themes_with_30_words_each():
    themes = list_themes()
    assert [t["id"] for t in themes] == [
        "school_life",
        "food_and_drink",
        "animals_nature",
        "family_home",
        "daily_routines",
    ]
    for theme in themes:
        assert len(load_words(theme["id"])) == 30
        assert theme["title"] and theme["title_zh"] and theme["emoji"]


def test_theme_lookup_rejects_unknown_or_path_like_names():
    assert get_theme("food_and_drink")["title"] == "Food and Drink"
    with pytest.raises(ValueError):
        load_words("../../etc/passwd")
    with pytest.raises(ValueError):
        get_theme("unknown")


def test_word_ids_are_unique_across_all_themes():
    ids = [w["id"] for t in list_themes() for w in load_words(t["id"])]
    assert len(ids) == 150
    assert len(set(ids)) == len(ids)


def all_words():
    return [w for theme in list_themes() for w in load_words(theme["id"])]


def test_every_word_has_required_non_empty_fields():
    for w in all_words():
        for field in REQUIRED:
            assert field in w, f"{w.get('id')} missing {field}"
            assert isinstance(w[field], str) and w[field].strip(), (
                f"{w.get('id')} has empty {field}"
            )


def test_pos_is_allowed():
    for w in all_words():
        assert w["pos"] in ALLOWED_POS, f"{w['id']} bad pos {w['pos']}"


def test_color_is_hex():
    for w in all_words():
        assert HEX_RE.match(w["color"]), f"{w['id']} bad color {w['color']}"


def test_example_is_a_sentence_containing_the_word_or_chunk():
    for w in all_words():
        assert w["example"].strip()[-1] in ".!?", f"{w['id']} example not a sentence"
        low = w["example"].lower()
        stem = w["en"].lower().split("/")[0].strip()
        assert stem in low or w["chunk"].lower() in low, (
            f"{w['id']} example does not use the word"
        )


def test_chunk_is_short_phrase():
    for w in all_words():
        assert 1 <= len(w["chunk"].split()) <= 4, f"{w['id']} chunk too long"
