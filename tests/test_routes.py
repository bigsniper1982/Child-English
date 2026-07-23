"""Integration tests for learning, games, speaking, parent and health routes."""
from app import create_app
from app import progress as prog
from app.content import load_words, list_themes
from app.db import get_db, default_child_id
from app.games import make_listen_round, make_sentence_round


def test_healthz_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_theme_picker_lists_both_themes(auth_client):
    resp = auth_client.get("/themes")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    for theme in list_themes():
        assert theme["title"] in html
        assert theme["title_zh"] in html


def test_select_food_theme_changes_today_and_learn(auth_client):
    resp = auth_client.post("/theme/select", headers=auth_client.api_headers,
                            data={"theme": "food_and_drink"},
                            follow_redirects=False)
    assert resp.status_code == 302
    with auth_client.session_transaction() as sess:
        assert sess["theme"] == "food_and_drink"
    today = auth_client.get("/today").get_data(as_text=True)
    learn = auth_client.get("/learn").get_data(as_text=True)
    assert "Food and Drink" in today
    assert "food_apple" in learn


def test_select_unknown_theme_is_rejected(auth_client):
    resp = auth_client.post("/theme/select", headers=auth_client.api_headers,
                            data={"theme": "../../etc/passwd"})
    assert resp.status_code == 400
    with auth_client.session_transaction() as sess:
        assert sess.get("theme", "school_life") == "school_life"


def test_theme_progress_is_kept_separate(auth_client, app):
    auth_client.post("/learn/review", headers=auth_client.api_headers,
                     json={"word_id": "teacher", "correct": True})
    auth_client.post("/theme/select", headers=auth_client.api_headers,
                     data={"theme": "food_and_drink"})
    auth_client.post("/learn/review", headers=auth_client.api_headers,
                     json={"word_id": "food_apple", "correct": True})
    with app.app_context():
        child_id = default_child_id()
        school = prog.stats(child_id, theme="school_life")
        food = prog.stats(child_id, theme="food_and_drink")
        overall = prog.stats(child_id, theme=None)
        assert school["seen_words"] == 1 and school["total_words"] == 30
        assert food["seen_words"] == 1 and food["total_words"] == 30
        assert overall["seen_words"] == 2 and overall["total_words"] == 60


def test_food_theme_games_only_use_food_words(auth_client):
    auth_client.post("/theme/select", headers=auth_client.api_headers,
                     data={"theme": "food_and_drink"})
    auth_client.get("/games/listen")
    with auth_client.session_transaction() as sess:
        seed = sess["listen_seed"]
        assert sess["listen_theme"] == "food_and_drink"
    rnd = make_listen_round(seed=seed, theme="food_and_drink")
    assert all(q["answer_id"].startswith("food_") for q in rnd["questions"])


def test_food_theme_speaking_uses_cafe_scenario(auth_client):
    auth_client.post("/theme/select", headers=auth_client.api_headers,
                     data={"theme": "food_and_drink"})
    html = auth_client.get("/speaking").get_data(as_text=True)
    assert "Friendly Café" in html
    resp = auth_client.post("/speaking/attempt", headers=auth_client.api_headers,
                            json={"turn": 0, "text": "I would like some water please."})
    assert resp.status_code == 200
    assert resp.get_json()["hit"] is True


def test_speaking_attempt_stays_with_page_theme_after_other_tab_switch(auth_client, app):
    page = auth_client.get("/speaking").get_data(as_text=True)
    assert 'data-theme="school_life"' in page
    auth_client.post("/theme/select", headers=auth_client.api_headers,
                     data={"theme": "food_and_drink"})
    resp = auth_client.post("/speaking/attempt", headers=auth_client.api_headers,
                            json={"turn": 0,
                                  "text": "My favourite subject is science.",
                                  "theme": "school_life"})
    assert resp.status_code == 200
    assert resp.get_json()["hit"] is True
    with app.app_context():
        row = get_db().execute(
            "SELECT scenario FROM speaking_attempts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row["scenario"] == "school_helper"


def test_speaking_attempt_rejects_unknown_theme(auth_client):
    resp = auth_client.post("/speaking/attempt", headers=auth_client.api_headers,
                            json={"turn": 0, "text": "hello",
                                  "theme": "../../etc/passwd"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "bad theme"


def test_learn_review_writes_progress(auth_client, app):
    word_id = load_words()[0]["id"]
    resp = auth_client.post("/learn/review", headers=auth_client.api_headers,
                            json={"word_id": word_id, "correct": True})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["stars"] >= 1
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM vocab_progress WHERE word_id = ?", (word_id,)
        ).fetchone()
        assert row is not None
        assert row["box"] == 1
        assert row["correct_count"] == 1


def test_learn_review_practice_again_keeps_box_low(auth_client, app):
    word_id = load_words()[1]["id"]
    auth_client.post("/learn/review", headers=auth_client.api_headers, json={"word_id": word_id, "correct": False})
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM vocab_progress WHERE word_id = ?", (word_id,)
        ).fetchone()
        assert row["box"] == 0
        assert row["wrong_count"] == 1


def test_learn_review_rejects_unknown_word(auth_client):
    resp = auth_client.post("/learn/review", headers=auth_client.api_headers,
                            json={"word_id": "not_a_word", "correct": True})
    assert resp.status_code == 400


def test_listen_game_submit_saves_score(auth_client, app):
    # Render a round so the seed is stored in the session.
    auth_client.get("/games/listen")
    with auth_client.session_transaction() as sess:
        seed = sess["listen_seed"]
    rnd = make_listen_round(seed=seed)
    answers = {q["id"]: q["answer_id"] for q in rnd["questions"]}
    resp = auth_client.post("/games/listen/submit", headers=auth_client.api_headers, json={"answers": answers})
    data = resp.get_json()
    assert data["score"] == data["total"]
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM game_results WHERE game = 'listen'").fetchone()
        assert row["score"] == data["total"]


def test_sentence_game_submit_saves_score(auth_client, app):
    auth_client.get("/games/sentence")
    with auth_client.session_transaction() as sess:
        seed = sess["sentence_seed"]
    rnd = make_sentence_round(seed=seed)
    answers = {q["id"]: list(q["answer_tokens"]) for q in rnd["questions"]}
    resp = auth_client.post("/games/sentence/submit", headers=auth_client.api_headers, json={"answers": answers})
    data = resp.get_json()
    assert data["score"] == data["total"]
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM game_results WHERE game = 'sentence'").fetchone()
        assert row is not None


def test_listen_game_round_cannot_be_submitted_twice(auth_client, app):
    auth_client.get("/games/listen")
    with auth_client.session_transaction() as sess:
        seed = sess["listen_seed"]
    rnd = make_listen_round(seed=seed)
    answers = {q["id"]: q["answer_id"] for q in rnd["questions"]}
    first = auth_client.post("/games/listen/submit", headers=auth_client.api_headers,
                             json={"answers": answers})
    assert first.status_code == 200
    second = auth_client.post("/games/listen/submit", headers=auth_client.api_headers,
                              json={"answers": answers})
    assert second.status_code == 400


def test_sentence_game_round_cannot_be_submitted_twice(auth_client):
    auth_client.get("/games/sentence")
    with auth_client.session_transaction() as sess:
        seed = sess["sentence_seed"]
    rnd = make_sentence_round(seed=seed)
    answers = {q["id"]: list(q["answer_tokens"]) for q in rnd["questions"]}
    first = auth_client.post("/games/sentence/submit", headers=auth_client.api_headers,
                             json={"answers": answers})
    assert first.status_code == 200
    second = auth_client.post("/games/sentence/submit", headers=auth_client.api_headers,
                              json={"answers": answers})
    assert second.status_code == 400


def test_sqlite_uses_wal_and_busy_timeout(app):
    with app.app_context():
        db = get_db()
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        timeout = db.execute("PRAGMA busy_timeout").fetchone()[0]
        assert mode.lower() == "wal"
        assert timeout >= 5000


def test_speaking_attempt_records_and_gives_feedback(auth_client, app):
    resp = auth_client.post("/speaking/attempt", headers=auth_client.api_headers,
                            json={"turn": 0, "text": "My favourite subject is science."})
    data = resp.get_json()
    assert data["hit"] is True
    assert data["feedback"]
    assert "%" not in data["feedback"]
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM speaking_attempts WHERE scenario = 'school_helper'"
        ).fetchone()
        assert row is not None
        assert row["keyword_hit"] == 1


def test_speaking_attempt_bad_turn_rejected(auth_client):
    resp = auth_client.post("/speaking/attempt", headers=auth_client.api_headers, json={"turn": 99, "text": "hi"})
    assert resp.status_code == 400


def test_parent_clear_erases_data(auth_client, app):
    word_id = load_words()[0]["id"]
    auth_client.post("/learn/review", headers=auth_client.api_headers, json={"word_id": word_id, "correct": True})
    # confirm something exists
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) c FROM vocab_progress").fetchone()["c"] == 1

    # clear needs CSRF token
    import re
    html = auth_client.get("/parent").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    resp = auth_client.post("/parent/clear", data={"csrf_token": token},
                            follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) c FROM vocab_progress").fetchone()["c"] == 0
        child = get_db().execute("SELECT * FROM children").fetchone()
        assert child["stars"] == 0


def test_parent_privacy_copy_does_not_claim_browser_asr_is_local(auth_client):
    html = auth_client.get("/parent").get_data(as_text=True)
    assert "本站服务器不会接收或保存原始录音" in html
    assert "浏览器或其语音服务商可能处理语音" in html
    assert "不会上传或保存任何录音" not in html


def test_parent_clear_requires_csrf(auth_client):
    resp = auth_client.post("/parent/clear", data={})
    assert resp.status_code == 400


def test_default_child_profile_name(app):
    with app.app_context():
        cid = default_child_id()
        row = get_db().execute("SELECT * FROM children WHERE id = ?", (cid,)).fetchone()
        assert row["name"] == "英语小探险家"
