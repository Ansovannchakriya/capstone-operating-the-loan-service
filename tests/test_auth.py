"""The three API-key checks from Lesson 6.6, plus key rotation and no key in the logs."""
import logging

import pytest

PROTECTED = "/api/v1/applications"


def test_no_key_is_401(client):
    r = client.get(PROTECTED)
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_wrong_key_is_401(client):
    assert client.get(PROTECTED, headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_right_key_is_200(client, auth):
    assert client.get(PROTECTED, headers=auth).status_code == 200


def test_old_key_still_works_during_rotation(client):
    assert client.get(PROTECTED, headers={"Authorization": "Bearer old-key"}).status_code == 200


@pytest.mark.parametrize("path", ["/health", "/openapi.json", "/docs"])
def test_public_paths(client, path):
    assert client.get(path).status_code == 200


def test_key_is_never_logged(client, auth, caplog):
    with caplog.at_level(logging.DEBUG):
        client.get(PROTECTED, headers=auth)
        client.get(PROTECTED, headers={"Authorization": "Bearer wrong"})
    assert "test-key-not-a-secret" not in caplog.text
