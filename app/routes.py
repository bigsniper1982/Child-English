"""Child-facing and parent-facing pages."""
import datetime as dt
import random

from flask import (
    Blueprint, jsonify, redirect, render_template, request, session, url_for,
)

from app import games as game_engine
from app import progress as prog
from app.auth import login_required
from app.content import DEFAULT_THEME, get_theme, get_word, list_themes, load_words
from app.db import (
    add_stars, clear_child_data, default_child_id, get_child, get_db,
)
from app.dialogue import evaluate, get_scenario, get_turn, num_turns

bp = Blueprint("main", __name__)

NEW_WORDS_PER_DAY = 5


def _child():
    return default_child_id()


def _theme():
    theme = session.get("theme", DEFAULT_THEME)
    try:
        get_theme(theme)
    except ValueError:
        theme = DEFAULT_THEME
        session["theme"] = theme
    return theme


# --------------------------------------------------------------- health -------
@bp.route("/healthz")
def healthz():
    try:
        get_db().execute("SELECT 1")
        return jsonify(status="ok"), 200
    except Exception:  # pragma: no cover - defensive
        return jsonify(status="error"), 500


# ---------------------------------------------------------------- home --------
@bp.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("main.today"))
    return redirect(url_for("auth.login"))


@bp.route("/themes")
@login_required
def themes():
    current = _theme()
    return render_template("themes.html", themes=list_themes(), current=current)


@bp.route("/theme/select", methods=["POST"])
@login_required
def theme_select():
    theme = request.form.get("theme", "")
    try:
        get_theme(theme)
    except ValueError:
        return jsonify(error="unknown theme"), 400
    session["theme"] = theme
    # A round belongs to the theme it was created for; switching invalidates it.
    for key in ("listen_seed", "listen_theme", "sentence_seed", "sentence_theme",
                "frog_seed", "frog_theme"):
        session.pop(key, None)
    return redirect(url_for("main.today"))


@bp.route("/today")
@login_required
def today():
    child_id = _child()
    theme_id = _theme()
    theme = get_theme(theme_id)
    child = get_child(child_id)
    stats = prog.stats(child_id, theme=theme_id)
    seen = {row["word_id"] for row in get_db().execute(
        "SELECT word_id FROM vocab_progress WHERE child_id = ?", (child_id,)
    ).fetchall()}
    new_words = [word for word in load_words(theme_id)
                 if word["id"] not in seen][:NEW_WORDS_PER_DAY]
    return render_template(
        "today.html", child=child, stats=stats, theme=theme,
        speaking_title=get_scenario(theme_id)["title"],
        new_words=new_words, due_count=stats["due_words"],
    )


# --------------------------------------------------------------- learn --------
@bp.route("/learn")
@login_required
def learn():
    child_id = _child()
    theme_id = _theme()
    seen = {row["word_id"] for row in get_db().execute(
        "SELECT word_id FROM vocab_progress WHERE child_id = ?", (child_id,)
    ).fetchall()}
    theme_words = load_words(theme_id)
    new_words = [word for word in theme_words
                 if word["id"] not in seen][:NEW_WORDS_PER_DAY]
    if not new_words:
        return redirect(url_for("main.review"))
    return render_template("learn.html", words=new_words, mode="learn",
                           theme=get_theme(theme_id))


@bp.route("/review")
@login_required
def review():
    child_id = _child()
    theme_id = _theme()
    due = prog.due_words(child_id, theme=theme_id)
    mode = "review"
    word_ids = due
    if not due:
        mode = "practice"
        word_ids = prog.studied_words(child_id, theme_id)
    words = [get_word(word_id, theme_id) for word_id in word_ids]
    return render_template("learn.html", words=[word for word in words if word],
                           mode=mode, theme=get_theme(theme_id))


@bp.route("/learn/review", methods=["POST"])
@login_required
def learn_review():
    child_id = _child()
    data = request.get_json(silent=True) or request.form
    word_id = data.get("word_id")
    correct = str(data.get("correct")).lower() in ("true", "1", "yes")
    mode = data.get("mode", "learn")
    theme = _theme()
    if not get_word(word_id, theme):
        return jsonify(error="unknown word"), 400
    if mode not in ("learn", "review"):
        return jsonify(error="invalid review mode"), 400
    existing = get_db().execute(
        "SELECT 1 FROM vocab_progress WHERE child_id = ? AND word_id = ?",
        (child_id, word_id),
    ).fetchone()
    if mode == "learn" and existing:
        return jsonify(error="word already learned"), 409
    if mode == "review" and word_id not in prog.due_words(child_id, theme=theme):
        return jsonify(error="word is not due"), 409
    if mode == "learn" and not correct:
        row = prog.defer_word(child_id, word_id)
    else:
        row = prog.record_review(child_id, word_id, correct)
    if correct:
        add_stars(child_id, 1)
    child = get_child(child_id)
    return jsonify(ok=True, status=row["status"], box=row["box"],
                   stars=child["stars"], fox_stage=child["fox_stage"])


# --------------------------------------------------------------- games --------
@bp.route("/games")
@login_required
def games():
    return render_template("games.html", theme=get_theme(_theme()))


@bp.route("/games/listen")
@login_required
def games_listen():
    seed = random.randrange(1, 10_000_000)
    theme = _theme()
    session["listen_seed"] = seed
    session["listen_theme"] = theme
    rnd = game_engine.make_listen_round(seed=seed, theme=theme)
    return render_template("game_listen.html", rnd=rnd, theme=get_theme(theme))


@bp.route("/games/listen/submit", methods=["POST"])
@login_required
def games_listen_submit():
    child_id = _child()
    data = request.get_json(silent=True) or {}
    seed = session.pop("listen_seed", None)
    theme = session.pop("listen_theme", None)
    if seed is None or theme is None:
        return jsonify(error="no active round"), 400
    rnd = game_engine.make_listen_round(seed=seed, theme=theme)
    score, total = game_engine.grade_listen(rnd, data.get("answers", {}))
    _save_game(child_id, "listen", score, total)
    return jsonify(score=score, total=total, stars=score)


@bp.route("/games/sentence")
@login_required
def games_sentence():
    seed = random.randrange(1, 10_000_000)
    theme = _theme()
    session["sentence_seed"] = seed
    session["sentence_theme"] = theme
    rnd = game_engine.make_sentence_round(seed=seed, theme=theme)
    return render_template("game_sentence.html", rnd=rnd, theme=get_theme(theme))


@bp.route("/games/sentence/submit", methods=["POST"])
@login_required
def games_sentence_submit():
    child_id = _child()
    data = request.get_json(silent=True) or {}
    seed = session.pop("sentence_seed", None)
    theme = session.pop("sentence_theme", None)
    if seed is None or theme is None:
        return jsonify(error="no active round"), 400
    rnd = game_engine.make_sentence_round(seed=seed, theme=theme)
    score, total = game_engine.grade_sentence(rnd, data.get("answers", {}))
    _save_game(child_id, "sentence", score, total)
    return jsonify(score=score, total=total, stars=score)


@bp.route("/games/frog")
@login_required
def games_frog():
    seed = random.randrange(1, 10_000_000)
    theme = _theme()
    session["frog_seed"] = seed
    session["frog_theme"] = theme
    rnd = game_engine.make_frog_round(seed=seed, theme=theme)
    return render_template("game_frog.html", rnd=rnd, theme=get_theme(theme))


@bp.route("/games/frog/submit", methods=["POST"])
@login_required
def games_frog_submit():
    child_id = _child()
    data = request.get_json(silent=True) or {}
    answers = data.get("answers", {})
    if not isinstance(answers, dict):
        return jsonify(error="bad answers"), 400
    seed = session.pop("frog_seed", None)
    theme = session.pop("frog_theme", None)
    if seed is None or theme is None:
        return jsonify(error="no active round"), 400
    rnd = game_engine.make_frog_round(seed=seed, theme=theme)
    score, total = game_engine.grade_frog(rnd, answers)
    _save_game(child_id, "frog", score, total)
    return jsonify(score=score, total=total, stars=score)


def _save_game(child_id, game, score, total):
    get_db().execute(
        "INSERT INTO game_results (child_id, game, score, total, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (child_id, game, score, total, dt.date.today().isoformat()),
    )
    get_db().commit()
    from app.db import record_activity_day
    record_activity_day(child_id)
    if score:
        add_stars(child_id, score)


# ------------------------------------------------------------- speaking -------
@bp.route("/speaking")
@login_required
def speaking():
    theme = _theme()
    scenario = get_scenario(theme)
    turns = [dict(index=index, **get_turn(index, theme))
             for index in range(num_turns(theme))]
    return render_template("speaking.html", scenario=scenario, turns=turns,
                           theme=get_theme(theme))


@bp.route("/speaking/attempt", methods=["POST"])
@login_required
def speaking_attempt():
    child_id = _child()
    data = request.get_json(silent=True) or {}
    try:
        turn_index = int(data.get("turn", -1))
    except (TypeError, ValueError):
        turn_index = -1
    theme = data.get("theme") or _theme()
    try:
        scenario = get_scenario(theme)
    except ValueError:
        return jsonify(error="bad theme"), 400
    if not (0 <= turn_index < num_turns(theme)):
        return jsonify(error="bad turn"), 400
    result = evaluate(turn_index, data.get("text", ""), theme)
    # Persist only the *outcome*, never the raw audio or full transcript.
    get_db().execute(
        "INSERT INTO speaking_attempts"
        " (child_id, scenario, turn_index, keyword_hit, complete, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (child_id, scenario["id"], turn_index,
         1 if result["hit"] else 0, 1 if result["complete_sentence"] else 0,
         dt.date.today().isoformat()),
    )
    get_db().commit()
    from app.db import record_activity_day
    record_activity_day(child_id)
    if result["stars"]:
        add_stars(child_id, result["stars"])
    child = get_child(child_id)
    result["total_stars"] = child["stars"]
    result["fox_stage"] = child["fox_stage"]
    return jsonify(result)


# ----------------------------------------------------------------- pet --------
@bp.route("/pet")
@login_required
def pet():
    child_id = _child()
    child = get_child(child_id)
    stats = prog.stats(child_id, theme=None)
    return render_template("pet.html", child=child, stats=stats)


# --------------------------------------------------------------- parent -------
@bp.route("/parent")
@login_required
def parent():
    child_id = _child()
    child = get_child(child_id)
    stats = prog.stats(child_id, theme=None)
    theme_stats = [
        dict(theme=theme, stats=prog.stats(child_id, theme=theme["id"]))
        for theme in list_themes()
    ]
    return render_template("parent.html", child=child, stats=stats,
                           theme_stats=theme_stats)


@bp.route("/parent/clear", methods=["POST"])
@login_required
def parent_clear():
    child_id = _child()
    clear_child_data(child_id)
    return redirect(url_for("main.parent"))
