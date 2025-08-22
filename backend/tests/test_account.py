import sys
from pathlib import Path

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from backend.server import main

client = TestClient(main.app)


def test_register_and_verify_flow():
    email = "alice@example.com"
    username = "alice"
    resp = client.post("/api/v1/register", json={"username": username, "email": email})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Code should be stored in pending codes
    code = main.pending_codes[email]["code"]
    assert isinstance(code, str) and len(code) == 6

    bad = client.post("/api/v1/verify", json={"email": email, "code": "000000"})
    assert bad.status_code == 400

    good = client.post("/api/v1/verify", json={"email": email, "code": code})
    assert good.status_code == 200
    assert good.json()["ok"] is True

    # Account moved from pending to accounts store
    assert email in main.accounts
    assert email not in main.pending_codes
    assert main.accounts[email]["username"] == username
