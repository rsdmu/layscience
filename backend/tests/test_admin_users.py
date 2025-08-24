import sys
from pathlib import Path

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from backend.server import main

client = TestClient(main.app)


def test_admin_users_authorized(monkeypatch):
    token = "s3cr3t"
    monkeypatch.setattr(main, "ADMIN_TOKEN", token)
    monkeypatch.setattr(
        main,
        "accounts",
        {
            "alice@example.com": {"username": "alice"},
            "bob@example.com": {"username": "bob"},
        },
    )
    resp = client.get("/api/v1/admin/users", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert {"email": "alice@example.com", "username": "alice"} in data
    assert {"email": "bob@example.com", "username": "bob"} in data


def test_admin_users_unauthorized(monkeypatch):
    monkeypatch.setattr(main, "ADMIN_TOKEN", "s3cr3t")
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 401
