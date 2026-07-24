"""Two playable vocabulary mini-games.

* Listen & Choose  – hear a word, tap the matching picture/word.
* Build a Sentence – drag scrambled word-blocks into the right order.

All round generation is seeded so it is deterministic (and therefore
testable), yet varies from round to round. Grading is pure.
"""
import random

from app.content import load_words

NUM_LISTEN_QUESTIONS = 5
NUM_SENTENCE_QUESTIONS = 5
NUM_FROG_QUESTIONS = 5
LISTEN_OPTIONS = 4
FROG_OPTIONS = 4


def _rng(seed):
    return random.Random(seed)


def make_listen_round(seed=None, theme="school_life"):
    """Build a Listen & Choose round.

    Each question plays a target word; the child picks it from ``LISTEN_OPTIONS``
    picture/word cards.
    """
    rng = _rng(seed)
    words = load_words(theme)
    targets = rng.sample(words, NUM_LISTEN_QUESTIONS)
    questions = []
    for i, target in enumerate(targets):
        distractors = rng.sample([w for w in words if w["id"] != target["id"]],
                                  LISTEN_OPTIONS - 1)
        options = [target] + distractors
        rng.shuffle(options)
        questions.append({
            "id": f"q{i}",
            "prompt_en": target["en"],
            "answer_id": target["id"],
            "options": [
                {"id": o["id"], "en": o["en"], "zh": o["zh"],
                 "emoji": o["emoji"], "color": o["color"]}
                for o in options
            ],
        })
    return {"game": "listen", "seed": seed, "questions": questions}


def grade_listen(rnd, answers):
    """Return ``(score, total)`` for a Listen round.

    ``answers`` maps question id -> chosen option id.
    """
    total = len(rnd["questions"])
    score = 0
    for q in rnd["questions"]:
        if answers.get(q["id"]) == q["answer_id"]:
            score += 1
    return score, total


def make_frog_round(seed=None, theme="school_life"):
    """Build a Find the Word round that moves a frog across the river."""
    rng = _rng(seed)
    words = load_words(theme)
    targets = rng.sample(words, NUM_FROG_QUESTIONS)
    questions = []
    for index, target in enumerate(targets):
        distractors = rng.sample(
            [word for word in words if word["id"] != target["id"]],
            FROG_OPTIONS - 1,
        )
        options = [target] + distractors
        rng.shuffle(options)
        questions.append({
            "id": f"f{index}",
            "prompt_zh": target["zh"],
            "emoji": target["emoji"],
            "answer_id": target["id"],
            "options": [
                {"id": option["id"], "en": option["en"]}
                for option in options
            ],
        })
    return {"game": "frog", "seed": seed, "questions": questions}


def grade_frog(rnd, answers):
    """Score the first submitted choice for each frog jump."""
    total = len(rnd["questions"])
    score = sum(
        1 for question in rnd["questions"]
        if answers.get(question["id"]) == question["answer_id"]
    )
    return score, total


def tokenize_sentence(sentence):
    """Split an example sentence into clean word-blocks (punctuation kept off)."""
    cleaned = sentence.replace(".", "").replace("!", "").replace("?", "")
    return [t for t in cleaned.split() if t]


def make_sentence_round(seed=None, theme="school_life"):
    """Build a Build-a-Sentence round from real example sentences."""
    rng = _rng(seed)
    words = load_words(theme)
    usable = [w for w in words if len(tokenize_sentence(w["example"])) >= 3]
    picks = rng.sample(usable, NUM_SENTENCE_QUESTIONS)
    questions = []
    for i, w in enumerate(picks):
        answer_tokens = tokenize_sentence(w["example"])
        scrambled = answer_tokens[:]
        # shuffle until it differs (unless the sentence is trivially symmetric)
        for _ in range(10):
            rng.shuffle(scrambled)
            if scrambled != answer_tokens:
                break
        questions.append({
            "id": f"s{i}",
            "word_id": w["id"],
            "hint_zh": w["zh"],
            "tokens": scrambled,
            "answer_tokens": answer_tokens,
        })
    return {"game": "sentence", "seed": seed, "questions": questions}


def grade_sentence(rnd, answers):
    """Return ``(score, total)`` for a Build-a-Sentence round.

    ``answers`` maps question id -> list of tokens in the child's order.
    Comparison is case-insensitive.
    """
    total = len(rnd["questions"])
    score = 0
    for q in rnd["questions"]:
        submitted = answers.get(q["id"])
        if not submitted:
            continue
        if [t.lower() for t in submitted] == [t.lower() for t in q["answer_tokens"]]:
            score += 1
    return score, total
