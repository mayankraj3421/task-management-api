"""
Unit tests for the Task Management API.
Run with:  pytest -v   (from the backend/ directory)
"""

import os
import sys
import tempfile
import pytest

# Make sure we can import app.py from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as flask_app_module  # noqa: E402


@pytest.fixture
def client():
    # Use a temporary SQLite file for each test run so tests don't pollute
    # the real dev database and don't interfere with each other.
    db_fd, db_path = tempfile.mkstemp()
    flask_app_module.app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    flask_app_module.app.config["TESTING"] = True

    with flask_app_module.app.test_client() as client:
        with flask_app_module.app.app_context():
            flask_app_module.db.create_all()
        yield client
        with flask_app_module.app.app_context():
            flask_app_module.db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


def register(client, username="alice", password="password123"):
    return client.post("/api/register", json={"username": username, "password": password})


def login(client, username="alice", password="password123"):
    return client.post("/api/login", json={"username": username, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------
def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_register_success(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert "access_token" in body
    assert body["user"]["username"] == "alice"


def test_register_duplicate_username(client):
    register(client)
    resp = register(client)
    assert resp.status_code == 409


def test_register_short_password(client):
    resp = client.post("/api/register", json={"username": "bob", "password": "123"})
    assert resp.status_code == 400


def test_login_success(client):
    register(client)
    resp = login(client)
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_wrong_password(client):
    register(client)
    resp = login(client, password="wrongpass")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Task CRUD tests
# ---------------------------------------------------------------------------
def get_token(client):
    register(client)
    return login(client).get_json()["access_token"]


def test_create_task_requires_auth(client):
    resp = client.post("/api/tasks", json={"title": "No auth task"})
    assert resp.status_code == 401


def test_create_task(client):
    token = get_token(client)
    resp = client.post(
        "/api/tasks",
        json={"title": "Write tests", "description": "cover the API"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "Write tests"
    assert body["status"] == "pending"


def test_create_task_missing_title(client):
    token = get_token(client)
    resp = client.post("/api/tasks", json={}, headers=auth_header(token))
    assert resp.status_code == 400


def test_list_tasks(client):
    token = get_token(client)
    client.post("/api/tasks", json={"title": "Task 1"}, headers=auth_header(token))
    client.post("/api/tasks", json={"title": "Task 2"}, headers=auth_header(token))

    resp = client.get("/api/tasks", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_filter_tasks_by_status(client):
    token = get_token(client)
    client.post(
        "/api/tasks", json={"title": "Done task", "status": "done"}, headers=auth_header(token)
    )
    client.post(
        "/api/tasks", json={"title": "Pending task", "status": "pending"}, headers=auth_header(token)
    )

    resp = client.get("/api/tasks?status=done", headers=auth_header(token))
    assert resp.status_code == 200
    tasks = resp.get_json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Done task"


def test_get_single_task(client):
    token = get_token(client)
    created = client.post(
        "/api/tasks", json={"title": "Solo task"}, headers=auth_header(token)
    ).get_json()

    resp = client.get(f"/api/tasks/{created['id']}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Solo task"


def test_update_task(client):
    token = get_token(client)
    created = client.post(
        "/api/tasks", json={"title": "Old title"}, headers=auth_header(token)
    ).get_json()

    resp = client.put(
        f"/api/tasks/{created['id']}",
        json={"title": "New title", "status": "in_progress"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New title"
    assert body["status"] == "in_progress"


def test_delete_task(client):
    token = get_token(client)
    created = client.post(
        "/api/tasks", json={"title": "Delete me"}, headers=auth_header(token)
    ).get_json()

    resp = client.delete(f"/api/tasks/{created['id']}", headers=auth_header(token))
    assert resp.status_code == 200

    resp2 = client.get(f"/api/tasks/{created['id']}", headers=auth_header(token))
    assert resp2.status_code == 404


def test_task_not_found(client):
    token = get_token(client)
    resp = client.get("/api/tasks/9999", headers=auth_header(token))
    assert resp.status_code == 404


def test_users_cannot_see_others_tasks(client):
    # alice creates a task
    token_alice = get_token(client)
    created = client.post(
        "/api/tasks", json={"title": "Alice's task"}, headers=auth_header(token_alice)
    ).get_json()

    # bob registers and logs in
    register(client, username="bob", password="password123")
    token_bob = login(client, username="bob", password="password123").get_json()["access_token"]

    # bob should not be able to see alice's task
    resp = client.get(f"/api/tasks/{created['id']}", headers=auth_header(token_bob))
    assert resp.status_code == 404
