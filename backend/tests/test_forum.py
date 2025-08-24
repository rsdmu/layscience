import os
import sys
import importlib
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[2]))


def test_topic_and_reply(tmp_path, monkeypatch):
    monkeypatch.setenv("FORUM_DB_PATH", str(tmp_path / "forum.sqlite3"))
    import backend.server.services.forum as forum
    import backend.server.main as main
    importlib.reload(forum)
    importlib.reload(main)

    client = TestClient(main.app)

    # create topic
    resp = client.post("/api/v1/feedback/topics", json={"title": "Hello", "body": "World"})
    assert resp.status_code == 200
    topic_id = resp.json()["id"]

    # list topics
    resp = client.get("/api/v1/feedback/topics")
    assert resp.status_code == 200
    topics = resp.json()["topics"]
    assert any(t["id"] == topic_id for t in topics)

    # create reply
    resp = client.post(f"/api/v1/feedback/topics/{topic_id}/replies", json={"body": "Nice"})
    assert resp.status_code == 200

    # list replies
    resp = client.get(f"/api/v1/feedback/topics/{topic_id}/replies")
    assert resp.status_code == 200
    replies = resp.json()["replies"]
    assert replies and replies[0]["body"] == "Nice"
