"""Login, CSRF, rate limiting and route-protection tests."""
import re

from tests.conftest import PASSWORD, _csrf


def test_login_success_sets_session(client):
    token = _csrf(client)
    resp = client.post("/login", data={"password": PASSWORD, "csrf_token": token},
                       follow_redirects=False)
    assert resp.status_code == 302
    assert "/today" in resp.headers["Location"]


def test_login_failure_shows_error(client):
    token = _csrf(client)
    resp = client.post("/login", data={"password": "wrong", "csrf_token": token})
    assert resp.status_code == 200
    assert "not right" in resp.get_data(as_text=True)


def test_login_rate_limited_after_max_attempts(client):
    token = _csrf(client)
    last = None
    for _ in range(6):
        last = client.post("/login", data={"password": "nope", "csrf_token": token})
    assert last.status_code == 429
    # even the correct password is refused while locked
    locked = client.post("/login", data={"password": PASSWORD, "csrf_token": token})
    assert locked.status_code == 429


def test_login_preserves_safe_deep_link(client):
    html = client.get("/login?next=/speaking").get_data(as_text=True)
    assert 'action="/login?next=/speaking"' in html
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match
    token = match.group(1)
    resp = client.post("/login?next=/speaking",
                       data={"password": PASSWORD, "csrf_token": token},
                       follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/speaking")


def test_login_rejects_scheme_relative_redirect(client):
    html = client.get("/login?next=//evil.example").get_data(as_text=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match
    token = match.group(1)
    resp = client.post("/login?next=//evil.example",
                       data={"password": PASSWORD, "csrf_token": token},
                       follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/today")
    assert "evil.example" not in resp.headers["Location"]


def test_proxy_rate_limit_is_per_forwarded_ip(client):
    token = _csrf(client)
    for _ in range(5):
        client.post("/login", headers={"X-Forwarded-For": "198.51.100.10"},
                    data={"password": "wrong", "csrf_token": token})
    resp = client.post("/login", headers={"X-Forwarded-For": "198.51.100.11"},
                       data={"password": PASSWORD, "csrf_token": token},
                       follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/today")


def test_csrf_required_on_post(client):
    # No csrf token -> rejected.
    resp = client.post("/login", data={"password": PASSWORD})
    assert resp.status_code == 400


def test_protected_route_redirects_when_logged_out(client):
    resp = client.get("/today", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_protected_routes_all_redirect(client):
    for path in ("/learn", "/review", "/games", "/speaking", "/pet", "/parent"):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 302, path
        assert "/login" in resp.headers["Location"], path


def test_logged_in_can_reach_today(auth_client):
    resp = auth_client.get("/today")
    assert resp.status_code == 200


def test_login_page_has_csrf_field(client):
    html = client.get("/login").get_data(as_text=True)
    assert re.search(r'name="csrf_token"', html)


def test_no_hardcoded_credentials_when_hash_missing(app, client):
    # Remove configured hash: no password should ever work.
    app.config["FAMILY_PASSWORD_HASH"] = None
    token = _csrf(client)
    resp = client.post("/login", data={"password": PASSWORD, "csrf_token": token})
    assert resp.status_code == 200
    assert "not right" in resp.get_data(as_text=True)
