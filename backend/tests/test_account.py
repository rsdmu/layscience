import sys
import json
from pathlib import Path

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from backend.server import main

client = TestClient(main.app)


def test_register_and_verify_flow(monkeypatch):
    email = "alice@example.com"
    username = "alice"
    monkeypatch.setattr(main, "_generate_code", lambda: "123456")
    resp = client.post("/api/v1/register", json={"username": username, "email": email})
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"

    record = main.pending_codes[email]
    assert record["code_hash"] == main._hash_code("123456")

    bad = client.post("/api/v1/verify", json={"email": email, "code": "000000"})
    assert bad.status_code == 400

    good = client.post("/api/v1/verify", json={"email": email, "code": "123456"})
    assert good.status_code == 200
    assert good.json()["status"] == "verified"

    # Account moved from pending to accounts store
    assert email in main.accounts
    assert email not in main.pending_codes
    assert main.accounts[email]["username"] == username


def test_delete_account_success(monkeypatch, tmp_path):
    email = "bob@example.com"
    monkeypatch.setattr(main, "accounts", {email: {"username": "bob"}})
    monkeypatch.setattr(main, "ACCOUNTS_PATH", str(tmp_path / "accounts.json"))
    resp = client.request("DELETE", "/api/v1/account", json={"email": email})
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    assert email not in main.accounts
    with open(tmp_path / "accounts.json", "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert email not in data


def test_delete_account_missing(monkeypatch):
    monkeypatch.setattr(main, "accounts", {})
    resp = client.request("DELETE", "/api/v1/account", json={"email": "ghost@example.com"})
    assert resp.status_code == 404
