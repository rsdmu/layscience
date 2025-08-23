import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.server import main

client = TestClient(main.app)


def test_register_sends_email(monkeypatch):
    """Registration should attempt to send an email even if SMTP_PORT is unset."""
    captured = {}

    class DummySMTP:
        def __init__(self, host, port):
            captured["host"] = host
            captured["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def ehlo(self):
            captured["ehlo"] = captured.get("ehlo", 0) + 1

        def starttls(self):
            captured["tls"] = True

        def login(self, user, password):
            captured["login"] = (user, password)

        def send_message(self, msg):
            captured["to"] = msg["To"]
            captured["body"] = msg.get_content()

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    # Intentionally do not set SMTP_PORT to rely on default 587
    monkeypatch.setenv("SMTP_USER", "no-reply@example.com")
    monkeypatch.setenv("SMTP_PASS", "secret")
    monkeypatch.setenv("SMTP_TLS", "1")
    monkeypatch.setattr(main.smtplib, "SMTP", DummySMTP)

    resp = client.post(
        "/api/v1/register", json={"username": "alice", "email": "alice@example.com"}
    )
    assert resp.status_code == 200
    assert captured["host"] == "smtp.example.com"
    assert captured["port"] == 587
    assert captured["to"] == "alice@example.com"
    assert "verification code" in captured["body"].lower()
