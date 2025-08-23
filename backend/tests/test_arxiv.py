import httpx
import pytest
from fastapi.testclient import TestClient

from backend.server.main import app
from backend.server.services import arxiv

SAMPLE_FEED = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <title>Sample Paper</title>
    <summary>Example</summary>
    <published>2020-01-01T00:00:00Z</published>
    <updated>2020-01-02T00:00:00Z</updated>
    <author><name>John Doe</name></author>
    <author><name>Jane Smith</name></author>
    <link rel='alternate' type='text/html' href='http://arxiv.org/abs/1234.5678v1'/>
    <link rel='related' type='application/pdf' href='http://arxiv.org/pdf/1234.5678v1'/>
    <category term='cs.AI' scheme='http://arxiv.org/schemas/atom'/>
  </entry>
</feed>"""


def fake_get(url, params=None, timeout=None):
    class R:
        status_code = 200
        text = SAMPLE_FEED

        def raise_for_status(self):
            pass

    return R()


def test_search_parses(monkeypatch):
    monkeypatch.setattr(httpx, "get", fake_get)
    res = arxiv.search("quantum")
    assert len(res) == 1
    item = res[0]
    assert item["id"] == "1234.5678v1"
    assert item["title"] == "Sample Paper"
    assert item["authors"] == ["John Doe", "Jane Smith"]
    assert item["links"]["pdf"].endswith("1234.5678v1")
    assert item["categories"] == ["cs.AI"]


def test_pdf_url():
    assert arxiv.pdf_url("1234.5678v1") == "https://arxiv.org/pdf/1234.5678v1.pdf"


def test_search_endpoint(monkeypatch):
    monkeypatch.setattr(httpx, "get", fake_get)
    client = TestClient(app)
    r = client.get("/api/v1/arxiv/search", params={"q": "quantum"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["results"][0]["id"] == "1234.5678v1"
