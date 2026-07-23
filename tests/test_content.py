"""Schema-validation tests for the School Life vocabulary content."""
import re

from app.content import load_words, ALLOWED_POS

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
REQUIRED = ("id", "en", "zh", "pos", "emoji", "color", "chunk", "example")


def test_exactly_30_words():
    words = load_words()
    assert len(words) == 30


def test_ids_are_unique():
    words = load_words()
    ids = [w["id"] for w in words]
    assert len(set(ids)) == len(ids)


def test_every_word_has_required_non_empty_fields():
    for w in load_words():
        for field in REQUIRED:
            assert field in w, f"{w.get('id')} missing {field}"
            assert isinstance(w[field], str) and w[field].strip(), (
                f"{w.get('id')} has empty {field}"
            )


def test_pos_is_allowed():
    for w in load_words():
        assert w["pos"] in ALLOWED_POS, f"{w['id']} bad pos {w['pos']}"


def test_color_is_hex():
    for w in load_words():
        assert HEX_RE.match(w["color"]), f"{w['id']} bad color {w['color']}"


def test_example_is_a_sentence_containing_the_word_or_chunk():
    for w in load_words():
        assert w["example"].strip()[-1] in ".!?", f"{w['id']} example not a sentence"
        low = w["example"].lower()
        stem = w["en"].lower().split("/")[0].strip()
        assert stem in low or w["chunk"].lower() in low, (
            f"{w['id']} example does not use the word"
        )


def test_chunk_is_short_phrase():
    for w in load_words():
        assert 1 <= len(w["chunk"].split()) <= 4, f"{w['id']} chunk too long"
