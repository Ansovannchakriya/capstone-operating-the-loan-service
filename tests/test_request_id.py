import json
import logging


def test_request_id_is_created(client):
    assert len(client.get("/health").headers["X-Request-ID"]) == 12


def test_request_id_is_kept_from_the_client(client):
    assert client.get("/health", headers={"X-Request-ID": "ticket-42"}).headers["X-Request-ID"] == "ticket-42"


def test_access_log_is_json_without_the_key(client, auth, caplog):
    with caplog.at_level(logging.INFO):
        client.get("/api/v1/applications?limit=1", headers={**auth, "X-Request-ID": "trace-me"})
    line = next(r.getMessage() for r in caplog.records if "trace-me" in r.getMessage())
    entry = json.loads(line)
    assert entry["path"] == "/api/v1/applications" and entry["status"] == 200
    assert "test-key-not-a-secret" not in caplog.text
