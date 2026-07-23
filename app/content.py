"""Safe loading and access helpers for original lesson themes."""
import json
import os
from functools import lru_cache

ALLOWED_POS = {"noun", "verb", "adjective", "adverb", "phrase"}
CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content")
DEFAULT_THEME = "school_life"

# Explicit allow-list: a session or request value can never become a file path.
_THEME_FILES = {
    "school_life": "school_life.json",
    "food_and_drink": "food_and_drink.json",
    "animals_nature": "animals_nature.json",
    "family_home": "family_home.json",
    "daily_routines": "daily_routines.json",
}


@lru_cache(maxsize=None)
def _load_theme(theme):
    if theme not in _THEME_FILES:
        raise ValueError(f"unknown theme: {theme}")
    path = os.path.join(CONTENT_DIR, _THEME_FILES[theme])
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("theme") != theme:
        raise ValueError(f"theme id mismatch: {theme}")
    return data


def get_theme(theme=DEFAULT_THEME):
    """Return public theme metadata without exposing its mutable word list."""
    data = _load_theme(theme)
    return {
        "id": data["theme"],
        "title": data["title"],
        "title_zh": data["title_zh"],
        "emoji": data["emoji"],
        "description": data.get("description", ""),
    }


def list_themes():
    """Return all available themes in their curriculum order."""
    return [get_theme(theme) for theme in _THEME_FILES]


def load_words(theme=DEFAULT_THEME):
    """Return the vocabulary entries for an allow-listed theme."""
    return _load_theme(theme)["words"]


def get_word(word_id, theme=DEFAULT_THEME):
    for word in load_words(theme):
        if word["id"] == word_id:
            return word
    return None


def word_ids(theme=DEFAULT_THEME):
    return [word["id"] for word in load_words(theme)]


def all_word_ids():
    return [word_id for theme in _THEME_FILES for word_id in word_ids(theme)]
