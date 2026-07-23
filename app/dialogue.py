"""Controlled 'School Helper' speaking scenario.

A tiny, deterministic dialogue engine. It never talks to an external model and
never claims to give an official exam score. Feedback is child-friendly: it
affirms first, corrects at most one thing at a time, and always lets the child
click to continue if speech was not recognised.
"""
import re

SCENARIO = {
    "id": "school_helper",
    "title": "School Helper",
    "intro": "Hi friend! I am your School Helper. Let's chat about your school day!",
    "disclaimer": (
        "This is friendly practice, not a real test. We just want to have fun "
        "talking in English."
    ),
    "turns": [
        {
            "question": "What is your favourite subject?",
            "sentence_frame": "My favourite subject is ____.",
            "keywords": ["science", "maths", "math", "english", "art", "music",
                         "sport", "reading", "history"],
        },
        {
            "question": "What do you bring to school in your schoolbag?",
            "sentence_frame": "I bring a ____ to school.",
            "keywords": ["book", "pencil", "pen", "ruler", "eraser", "lunch",
                         "water", "notebook"],
        },
        {
            "question": "What is your favourite after-school activity?",
            "sentence_frame": "After school I like to ____.",
            "keywords": ["play", "read", "draw", "paint", "run", "swim",
                         "dance", "sing", "football", "basketball"],
        },
        {
            "question": "Who do you play with at school?",
            "sentence_frame": "I play with my ____.",
            "keywords": ["friend", "friends", "classmate", "classmates",
                         "brother", "sister"],
        },
    ],
}


def num_turns():
    return len(SCENARIO["turns"])


def get_turn(index):
    return SCENARIO["turns"][index]


def _tokens(text):
    return re.findall(r"[a-zA-Z']+", text.lower())


def _is_complete_sentence(text):
    """A rough, kind heuristic: at least four words strung together."""
    return len(_tokens(text)) >= 4


# Words that make an off-script answer clearly unsafe/negative. Kept tiny and
# conservative; anything not flagged is treated as safe and gently redirected.
_UNSAFE = {"hate", "stupid", "kill", "hurt", "hell"}


def evaluate(turn_index, answer):
    """Score a child's spoken/typed answer for a turn.

    Returns a dict the UI can render directly. Never raises on empty input.
    """
    turn = get_turn(turn_index)
    text = (answer or "").strip()
    tokens = set(_tokens(text))

    result = {
        "hit": False,
        "off_script": False,
        "redirect": False,
        "allow_skip": False,
        "advance": False,
        "complete_sentence": False,
        "corrections": 0,
        "stars": 0,
        "matched": None,
        "feedback": "",
    }

    if not text:
        result["allow_skip"] = True
        result["feedback"] = (
            "I didn't quite hear you. Try again, or tap a word to keep going!"
        )
        return result

    matched = next((kw for kw in turn["keywords"] if kw in tokens), None)
    complete = _is_complete_sentence(text)
    result["complete_sentence"] = complete

    if matched:
        result["hit"] = True
        result["advance"] = True
        result["matched"] = matched
        stars = 1
        if complete:
            stars += 1
            result["feedback"] = (
                f"Wonderful! '{matched}' is a great answer, and you said a whole "
                "sentence. High five! ⭐"
            )
        else:
            # exactly one gentle correction: model the full sentence
            result["corrections"] = 1
            frame = turn["sentence_frame"].replace("____", matched)
            result["feedback"] = (
                f"Nice, '{matched}'! Now try the whole sentence: \"{frame}\""
            )
        result["stars"] = stars
        return result

    # No keyword. Is it clearly unsafe, or just off-script?
    if tokens & _UNSAFE:
        result["off_script"] = True
        result["redirect"] = True
        result["feedback"] = (
            "Let's use kind words. Back to school — " + turn["question"]
        )
        return result

    # Safe but off-script: affirm first, then bring back to the task.
    result["off_script"] = True
    result["redirect"] = True
    result["allow_skip"] = True
    frame = turn["sentence_frame"]
    result["feedback"] = (
        "That sounds fun! Now let's stay with school. "
        f"Try: \"{frame}\" You can also tap a word to help."
    )
    return result
