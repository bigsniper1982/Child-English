"""Deterministic, theme-scoped speaking scenarios with kind feedback."""
import re

SCENARIOS = {
    "school_life": {
        "id": "school_helper",
        "title": "School Helper",
        "intro": "Hi friend! I am your School Helper. Let's chat about your school day!",
        "topic": "school",
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
    },
    "food_and_drink": {
        "id": "friendly_cafe",
        "title": "Friendly Café",
        "intro": "Welcome to the Friendly Café! Let's order a tasty meal in English.",
        "topic": "food and drinks",
        "disclaimer": (
            "This is friendly practice, not a real test. Choose a helpful word and "
            "say as much as you can."
        ),
        "turns": [
            {
                "question": "What would you like to drink?",
                "sentence_frame": "I would like some ____, please.",
                "keywords": ["water", "milk", "juice"],
            },
            {
                "question": "What would you like to eat?",
                "sentence_frame": "I would like ____, please.",
                "keywords": ["rice", "noodles", "soup", "salad", "chicken", "fish",
                             "bread", "sandwich"],
            },
            {
                "question": "How does your food taste?",
                "sentence_frame": "It is ____.",
                "keywords": ["delicious", "sweet", "salty", "good", "tasty", "hot"],
            },
            {
                "question": "Would you like some fruit after your meal?",
                "sentence_frame": "Yes, I would like a ____.",
                "keywords": ["apple", "banana", "orange"],
            },
        ],
    },
    "animals_nature": {
        "id": "nature_explorer",
        "title": "Nature Explorer",
        "intro": "Welcome, explorer! Let's talk about animals and the world outside.",
        "topic": "animals and nature",
        "disclaimer": "This is friendly speaking practice. Use a word or a whole sentence.",
        "turns": [
            {
                "question": "Which animal do you like?",
                "sentence_frame": "I like the ____.",
                "keywords": ["dog", "cat", "bird", "rabbit", "horse", "panda",
                             "elephant", "lion", "tiger", "monkey", "bear"],
            },
            {
                "question": "Where does that animal live?",
                "sentence_frame": "It lives in the ____.",
                "keywords": ["forest", "river", "mountain", "garden", "farm", "water"],
            },
            {
                "question": "What can you see outside today?",
                "sentence_frame": "I can see a ____.",
                "keywords": ["tree", "flower", "bird", "butterfly", "bee", "sky",
                             "sun", "moon", "mountain", "river"],
            },
            {
                "question": "How can we help nature?",
                "sentence_frame": "We can ____ nature.",
                "keywords": ["protect", "clean", "help", "plant", "save", "recycle"],
            },
        ],
    },
    "family_home": {
        "id": "home_helper",
        "title": "Home Helper",
        "intro": "Hello! Let's talk about your family and how you help at home.",
        "topic": "family and home",
        "disclaimer": "This is friendly speaking practice. Share only simple, safe details.",
        "turns": [
            {
                "question": "Who is in your family?",
                "sentence_frame": "There is my ____ in my family.",
                "keywords": ["mother", "father", "parent", "brother", "sister", "baby",
                             "grandmother", "grandfather"],
            },
            {
                "question": "Which room do you like at home?",
                "sentence_frame": "I like the ____.",
                "keywords": ["bedroom", "bathroom", "kitchen", "living", "room", "garden"],
            },
            {
                "question": "What do you do to help at home?",
                "sentence_frame": "I help to ____.",
                "keywords": ["clean", "tidy", "cook", "wash", "share", "help"],
            },
            {
                "question": "What does your family do together?",
                "sentence_frame": "We ____ together.",
                "keywords": ["eat", "read", "play", "cook", "talk", "walk", "work"],
            },
        ],
    },
    "daily_routines": {
        "id": "day_planner",
        "title": "My Day Planner",
        "intro": "Let's plan a happy day from morning to bedtime!",
        "topic": "daily routines",
        "disclaimer": "This is friendly speaking practice, not a test or a strict timetable.",
        "turns": [
            {
                "question": "What time do you get up?",
                "sentence_frame": "I get up at ____.",
                "keywords": ["six", "seven", "eight", "six-thirty", "seven-thirty"],
            },
            {
                "question": "What do you do before school?",
                "sentence_frame": "Before school I ____.",
                "keywords": ["wash", "brush", "dress", "eat", "read", "walk"],
            },
            {
                "question": "What do you do after school?",
                "sentence_frame": "After school I ____.",
                "keywords": ["study", "play", "exercise", "read", "relax", "homework"],
            },
            {
                "question": "What do you do before bed?",
                "sentence_frame": "Before bed I ____.",
                "keywords": ["shower", "read", "brush", "relax", "sleep"],
            },
        ],
    },
}

# Backwards-compatible alias used by existing code and tests.
SCENARIO = SCENARIOS["school_life"]


def get_scenario(theme="school_life"):
    try:
        return SCENARIOS[theme]
    except KeyError as exc:
        raise ValueError(f"unknown dialogue theme: {theme}") from exc


def num_turns(theme="school_life"):
    return len(get_scenario(theme)["turns"])


def get_turn(index, theme="school_life"):
    return get_scenario(theme)["turns"][index]


def _tokens(text):
    return re.findall(r"[a-zA-Z']+", text.lower())


def _is_complete_sentence(text):
    """A rough, kind heuristic: at least four words strung together."""
    return len(_tokens(text)) >= 4


_UNSAFE = {"hate", "stupid", "kill", "hurt", "hell"}


def evaluate(turn_index, answer, theme="school_life"):
    """Evaluate one answer without storing audio or claiming an exam score."""
    scenario = get_scenario(theme)
    turn = get_turn(turn_index, theme)
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

    matched = next((keyword for keyword in turn["keywords"] if keyword in tokens), None)
    complete = _is_complete_sentence(text)
    result["complete_sentence"] = complete

    if matched:
        result["hit"] = True
        result["advance"] = True
        result["matched"] = matched
        result["stars"] = 1
        if complete:
            result["stars"] = 2
            result["feedback"] = (
                f"Wonderful! '{matched}' is a great answer, and you said a whole "
                "sentence. High five! ⭐"
            )
        else:
            result["corrections"] = 1
            frame = turn["sentence_frame"].replace("____", matched)
            result["feedback"] = (
                f"Nice, '{matched}'! Now try the whole sentence: \"{frame}\""
            )
        return result

    result["off_script"] = True
    result["redirect"] = True
    if tokens & _UNSAFE:
        result["feedback"] = (
            f"Let's use kind words. Back to {scenario['topic']} — {turn['question']}"
        )
        return result

    result["allow_skip"] = True
    result["feedback"] = (
        f"That sounds interesting! Now let's stay with {scenario['topic']}. "
        f"Try: \"{turn['sentence_frame']}\" You can also tap a word to help."
    )
    return result
