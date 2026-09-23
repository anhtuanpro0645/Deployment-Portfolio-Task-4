"""Tests for the Task 4.2 Flask application (written before the app - TDD)."""

import socket

import pytest

from app import MAX_NAME_LENGTH, create_app, get_port


@pytest.fixture
def client():
    application = create_app()
    application.config.update(TESTING=True)
    return application.test_client()


# ---------- Home page ----------


def test_home_returns_html_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_home_shows_container_hostname(client):
    response = client.get("/")

    assert socket.gethostname() in response.get_data(as_text=True)


# ---------- Health check ----------


def test_health_returns_ok_json(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


# ---------- Greet API ----------


def test_greet_returns_message_for_valid_name(client):
    response = client.get("/api/greet?name=Tuan")

    assert response.status_code == 200
    assert response.get_json() == {"message": "Hello, Tuan!"}


def test_greet_trims_surrounding_whitespace(client):
    response = client.get("/api/greet?name=%20%20Tuan%20%20")

    assert response.get_json() == {"message": "Hello, Tuan!"}


@pytest.mark.parametrize(
    "query",
    [
        "",  # missing name
        "?name=",  # empty name
        "?name=%20%20%20",  # whitespace only
        "?name=<script>alert(1)</script>",  # injection attempt
        "?name=Tuan123",  # digits not allowed
        f"?name={'a' * (MAX_NAME_LENGTH + 1)}",  # too long
    ],
)
def test_greet_rejects_invalid_names(client, query):
    response = client.get(f"/api/greet{query}")

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_greet_accepts_name_at_max_length(client):
    name = "a" * MAX_NAME_LENGTH

    response = client.get(f"/api/greet?name={name}")

    assert response.status_code == 200


# ---------- Configuration ----------


def test_get_port_defaults_when_env_missing(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)

    assert get_port() == 5000


def test_get_port_reads_env_variable(monkeypatch):
    monkeypatch.setenv("PORT", "8080")

    assert get_port() == 8080


@pytest.mark.parametrize("bad_value", ["abc", "0", "70000"])
def test_get_port_rejects_invalid_values(monkeypatch, bad_value):
    monkeypatch.setenv("PORT", bad_value)

    with pytest.raises(ValueError):
        get_port()
