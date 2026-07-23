"""Loading and access helpers for lesson content (School Life theme)."""
import json
import os
from functools import lru_cache

ALLOWED_POS = {"noun", "verb", "adjective", "adverb", "phrase"}

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content")


@lru_cache(maxsize=None)
def load_words(theme="school_life"):
    """Return the list of vocabulary entries for a theme."""
    path = os.path.join(CONTENT_DIR, f"{theme}.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["words"]


def get_word(word_id, theme="school_life"):
    for w in load_words(theme):
        if w["id"] == word_id:
            return w
    return None


def word_ids(theme="school_life"):
    return [w["id"] for w in load_words(theme)]
