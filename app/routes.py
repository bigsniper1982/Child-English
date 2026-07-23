"""Child-facing and parent-facing pages."""
import datetime as dt
import random

from flask import (
    Blueprint, jsonify, redirect, render_template, request, session, url_for,
)

from app import games as game_engine
from app import progress as prog
from app.auth import login_required
from app.content import get_word, load_words
from app.db import (
    add_stars, clear_child_data, default_child_id, get_child, get_db,
)
from app.dialogue import SCENARIO, evaluate, get_turn, num_turns

bp = Blueprint("main", __name__)

NEW_WORDS_PER_DAY = 5


def _child():
    return default_child_id()


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


@bp.route("/today")
@login_required
def today():
    child_id = _child()
    child = get_child(child_id)
    stats = prog.stats(child_id)
    seen = {r["word_id"] for r in get_db().execute(
        "SELECT word_id FROM vocab_progress WHERE child_id = ?", (child_id,)
    ).fetchall()}
    new_words = [w for w in load_words() if w["id"] not in seen][:NEW_WORDS_PER_DAY]
    return render_template(
        "today.html", child=child, stats=stats,
        new_words=new_words, due_count=stats["due_words"],
    )


# --------------------------------------------------------------- learn --------
@bp.route("/learn")
@login_required
def learn():
    child_id = _child()
    seen = {r["word_id"] for r in get_db().execute(
        "SELECT word_id FROM vocab_progress WHERE child_id = ?", (child_id,)
    ).fetchall()}
    new_words = [w for w in load_words() if w["id"] not in seen][:NEW_WORDS_PER_DAY]
    if not new_words:  # all learned once – let them study the full set again
        new_words = load_words()[:NEW_WORDS_PER_DAY]
    return render_template("learn.html", words=new_words, mode="learn")


@bp.route("/review")
@login_required
def review():
    child_id = _child()
    due = prog.due_words(child_id)
    words = [get_word(wid) for wid in due if get_word(wid)]
    return render_template("learn.html", words=words, mode="review")


@bp.route("/learn/review", methods=["POST"])
@login_required
def learn_review():
    child_id = _child()
    data = request.get_json(silent=True) or request.form
    word_id = data.get("word_id")
    correct = str(data.get("correct")).lower() in ("true", "1", "yes")
    if not get_word(word_id):
        return jsonify(error="unknown word"), 400
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
    return render_template("games.html")


@bp.route("/games/listen")
@login_required
def games_listen():
    seed = random.randrange(1, 10_000_000)
    session["listen_seed"] = seed
    rnd = game_engine.make_listen_round(seed=seed)
    return render_template("game_listen.html", rnd=rnd)


@bp.route("/games/listen/submit", methods=["POST"])
@login_required
def games_listen_submit():
    child_id = _child()
    data = request.get_json(silent=True) or {}
    seed = session.pop("listen_seed", None)
    if seed is None:
        return jsonify(error="no active round"), 400
    rnd = game_engine.make_listen_round(seed=seed)
    score, total = game_engine.grade_listen(rnd, data.get("answers", {}))
    _save_game(child_id, "listen", score, total)
    return jsonify(score=score, total=total, stars=score)


@bp.route("/games/sentence")
@login_required
def games_sentence():
    seed = random.randrange(1, 10_000_000)
    session["sentence_seed"] = seed
    rnd = game_engine.make_sentence_round(seed=seed)
    return render_template("game_sentence.html", rnd=rnd)


@bp.route("/games/sentence/submit", methods=["POST"])
@login_required
def games_sentence_submit():
    child_id = _child()
    data = request.get_json(silent=True) or {}
    seed = session.pop("sentence_seed", None)
    if seed is None:
        return jsonify(error="no active round"), 400
    rnd = game_engine.make_sentence_round(seed=seed)
    score, total = game_engine.grade_sentence(rnd, data.get("answers", {}))
    _save_game(child_id, "sentence", score, total)
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
    turns = [dict(index=i, **get_turn(i)) for i in range(num_turns())]
    return render_template("speaking.html", scenario=SCENARIO, turns=turns)


@bp.route("/speaking/attempt", methods=["POST"])
@login_required
def speaking_attempt():
    child_id = _child()
    data = request.get_json(silent=True) or {}
    try:
        turn_index = int(data.get("turn", -1))
    except (TypeError, ValueError):
        turn_index = -1
    if not (0 <= turn_index < num_turns()):
        return jsonify(error="bad turn"), 400
    result = evaluate(turn_index, data.get("text", ""))
    # Persist only the *outcome*, never the raw audio or full transcript.
    get_db().execute(
        "INSERT INTO speaking_attempts"
        " (child_id, scenario, turn_index, keyword_hit, complete, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (child_id, SCENARIO["id"], turn_index,
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
    stats = prog.stats(child_id)
    return render_template("pet.html", child=child, stats=stats)


# --------------------------------------------------------------- parent -------
@bp.route("/parent")
@login_required
def parent():
    child_id = _child()
    child = get_child(child_id)
    stats = prog.stats(child_id)
    return render_template("parent.html", child=child, stats=stats)


@bp.route("/parent/clear", methods=["POST"])
@login_required
def parent_clear():
    child_id = _child()
    clear_child_data(child_id)
    return redirect(url_for("main.parent"))
