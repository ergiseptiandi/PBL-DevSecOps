from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_version_reports_blue_green_info():
    res = client.get("/api/version")
    assert res.status_code == 200
    body = res.json()
    assert body["color"] == "blue"
    assert body["version"] == "9.9.9-test"


def test_security_headers_present():
    res = client.get("/api/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["content-security-policy"].startswith("default-src 'none'")
    assert res.headers["cache-control"] == "no-store"


def test_create_task_valid():
    res = client.post("/api/tasks", json={"title": "Review pipeline Trivy"})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Review pipeline Trivy"
    assert body["completed"] is False
    assert "id" in body and body["id"] > 0


def test_create_task_empty_title_rejected():
    res = client.post("/api/tasks", json={"title": "   "})
    assert res.status_code == 422


def test_create_task_too_long_rejected():
    res = client.post("/api/tasks", json={"title": "x" * 141})
    assert res.status_code == 422


def test_create_task_control_characters_rejected():
    res = client.post("/api/tasks", json={"title": "baris1\nbaris2"})
    assert res.status_code == 422


def test_create_task_sql_injection_is_stored_literally():
    payload = "'; DROP TABLE tasks;--"
    res = client.post("/api/tasks", json={"title": payload})
    assert res.status_code == 201
    assert res.json()["title"] == payload
    # tabel masih ada dan bisa dibaca
    assert client.get("/api/tasks").status_code == 200


def test_list_tasks_returns_created_task():
    client.post("/api/tasks", json={"title": "dari test list"})
    res = client.get("/api/tasks")
    assert res.status_code == 200
    titles = [t["title"] for t in res.json()]
    assert "dari test list" in titles


def test_patch_task_completed_strict_bool():
    created = client.post("/api/tasks", json={"title": "toggle me"}).json()

    res = client.patch(f"/api/tasks/{created['id']}", json={"completed": True})
    assert res.status_code == 200
    assert res.json()["completed"] is True

    # string "yes" tidak boleh lolos sebagai boolean
    res = client.patch(f"/api/tasks/{created['id']}", json={"completed": "yes"})
    assert res.status_code == 422


def test_patch_task_not_found():
    res = client.patch("/api/tasks/999999", json={"completed": True})
    assert res.status_code == 404


def test_delete_task_no_existence_leak():
    created = client.post("/api/tasks", json={"title": "hapus saya"}).json()

    assert client.delete(f"/api/tasks/{created['id']}").status_code == 204
    assert client.delete(f"/api/tasks/{created['id']}").status_code == 204
    assert client.delete("/api/tasks/999999").status_code == 204


def test_unknown_route_returns_json_404():
    res = client.get("/api/tidak-ada")
    assert res.status_code == 404
