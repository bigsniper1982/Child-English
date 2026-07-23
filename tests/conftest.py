import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.auth import reset_rate_limits

PASSWORD = "island-2026"


@pytest.fixture
def app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app({
        "TESTING": True,
        "DATABASE": path,
        "SECRET_KEY": "test-secret",
        "FAMILY_PASSWORD_HASH": generate_password_hash(PASSWORD),
        "MAX_LOGIN_ATTEMPTS": 5,
        "LOGIN_LOCKOUT_SECONDS": 300,
        "WTF_CSRF_ENABLED": False,
    })
    reset_rate_limits()
    yield app
    os.unlink(path)


@pytest.fixture
def client(app):
    return app.test_client()


def _csrf(client):
    """Fetch a valid CSRF token from the login page session."""
    resp = client.get("/login")
    html = resp.get_data(as_text=True)
    # token is embedded in a hidden input
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None


def csrf_from(client, path="/today"):
    """Extract the CSRF token embedded on any authenticated page."""
    import re
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None


@pytest.fixture
def auth_client(client):
    token = _csrf(client)
    client.post("/login", data={"password": PASSWORD, "csrf_token": token})
    # Expose a valid token + JSON header helper the way the front-end sends it.
    client.csrf = csrf_from(client)
    client.api_headers = {"X-CSRF-Token": client.csrf}
    return client
