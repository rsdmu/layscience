import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from backend.server import main

client = TestClient(main.app)


def test_resend_reuses_code(monkeypatch):
    email = "bob@example.com"
    monkeypatch.setattr(main, "_generate_code", lambda: "654321")
    client.post("/api/v1/register", json={"username": "bob", "email": email})
    # change generator to ensure resend doesn't use new code
    monkeypatch.setattr(main, "_generate_code", lambda: "999999")
    resp = client.post("/api/v1/resend", json={"email": email})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resent"
    assert main.pending_codes[email]["code"] == "654321"


def test_code_expiry(monkeypatch):
    email = "carol@example.com"
    monkeypatch.setattr(main, "_generate_code", lambda: "111111")
    client.post("/api/v1/register", json={"username": "carol", "email": email})
    # force expiry
    main.pending_codes[email]["expires_at"] = datetime.utcnow() - timedelta(seconds=1)
    bad = client.post("/api/v1/verify", json={"email": email, "code": "111111"})
    assert bad.status_code == 400
