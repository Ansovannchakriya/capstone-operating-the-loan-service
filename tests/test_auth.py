"""The three API-key checks from Lesson 6.6 Hands-on 2: /health open, no key 401, right key 200.
Plus a wrong key, and the key never appearing in the logs."""
import logging

PROTECTED = "/api/v1/applications"


def test_health_is_open(client):
    assert client.get("/health").json()["status"] == "ok"


def test_no_key_is_401(client):
    assert client.get(PROTECTED).status_code == 401


def test_wrong_key_is_401(client):
    assert client.get(PROTECTED, headers={"X-API-Key": "wrong"}).status_code == 401


def test_right_key_is_200(client, auth):
    r = client.get(PROTECTED, headers=auth)
    assert r.status_code == 200
    assert "items" in r.json()


def test_docs_stay_open(client):
    assert client.get("/docs").status_code == 200


def test_key_is_never_logged(client, auth, caplog):
    with caplog.at_level(logging.DEBUG):
        client.get(PROTECTED, headers=auth)
        client.get(PROTECTED, headers={"X-API-Key": "wrong"})
    assert "test-key-not-a-secret" not in caplog.text
