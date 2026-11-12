NEW = {"borrower_id": 1044, "amount_usd": 1500, "term_months": 12}


def test_health_is_public_and_shows_sha(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["git_sha"] == "abc1234"
    assert body["model_version"] == "loan-default-v1"


def test_create_and_get_application(client, auth):
    r = client.post("/api/v1/applications", json=NEW, headers=auth)
    assert r.status_code == 201
    app = r.json()
    assert app["status"] == "pending"
    assert r.headers["Location"] == f"/api/v1/applications/{app['id']}"
    assert client.get(f"/api/v1/applications/{app['id']}", headers=auth).json() == app


def test_amount_outside_rule_is_422_with_text_detail(client, auth):
    r = client.post("/api/v1/applications", json={**NEW, "amount_usd": 9000}, headers=auth)
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


def test_unknown_borrower_is_422(client, auth):
    assert client.post("/api/v1/applications", json={**NEW, "borrower_id": 1}, headers=auth).status_code == 422


def test_missing_application_is_404(client, auth):
    assert client.get("/api/v1/applications/999999", headers=auth).status_code == 404


def test_decide_once_then_409(client, auth):
    app_id = client.post("/api/v1/applications", json=NEW, headers=auth).json()["id"]
    r = client.patch(f"/api/v1/applications/{app_id}", json={"status": "approved"}, headers=auth)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    r = client.patch(f"/api/v1/applications/{app_id}", json={"status": "rejected"}, headers=auth)
    assert r.status_code == 409
    assert r.json()["detail"] == f"application {app_id} is already approved"


def test_status_pending_is_not_allowed_in_patch(client, auth):
    app_id = client.post("/api/v1/applications", json=NEW, headers=auth).json()["id"]
    assert client.patch(f"/api/v1/applications/{app_id}", json={"status": "pending"},
                        headers=auth).status_code == 422


def test_list_filters_and_cursor(client, auth):
    for _ in range(3):
        client.post("/api/v1/applications", json={**NEW, "borrower_id": 1042}, headers=auth)
    page1 = client.get("/api/v1/applications?province=Siem Reap&limit=2", headers=auth).json()
    assert len(page1["items"]) == 2 and page1["next_cursor"] is not None
    assert page1["items"][0]["id"] > page1["items"][1]["id"]  # newest first
    page2 = client.get(f"/api/v1/applications?province=Siem Reap&limit=2&after={page1['next_cursor']}",
                       headers=auth).json()
    assert all(a["id"] < page1["next_cursor"] for a in page2["items"])


def test_prediction_is_stored_with_model_version(client, auth):
    app_id = client.post("/api/v1/applications", json=NEW, headers=auth).json()["id"]
    r = client.post(f"/api/v1/applications/{app_id}/predictions", headers=auth)
    assert r.status_code == 201
    body = r.json()
    assert 0 <= body["default_probability"] <= 1
    assert body["model_version"] == "loan-default-v1"


def test_borrower_applications(client, auth):
    assert client.get("/api/v1/borrowers/1044/applications", headers=auth).status_code == 200
    assert client.get("/api/v1/borrowers/1/applications", headers=auth).status_code == 404


def test_openapi_has_every_spec_path(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/api/v1/applications", "/api/v1/applications/{application_id}",
              "/api/v1/applications/{application_id}/predictions",
              "/api/v1/borrowers/{borrower_id}/applications", "/health"]:
        assert p in paths


def test_security_headers(client):
    assert "max-age=31536000" in client.get("/health").headers["Strict-Transport-Security"]
