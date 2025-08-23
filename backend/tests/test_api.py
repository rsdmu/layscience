import os
import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Ensure DRY_RUN for tests
os.environ['DRY_RUN'] = '1'

from backend.server import main
from backend.server.services import pdfio, fetcher

client = TestClient(main.app)


def test_start_summary_missing_input():
    resp = client.post('/api/v1/summaries', json={})
    assert resp.status_code == 400
    body = resp.json()
    assert body['error'] == 'missing_input'


def test_pdf_upload_summary(monkeypatch):
    def fake_extract(path: str):
        return 'PDF content about biology.', {'title': 'Bio Paper', 'authors': 'A'}
    monkeypatch.setattr(pdfio, 'extract_text_and_meta', fake_extract)
    files = {'pdf': ('paper.pdf', b'fake', 'application/pdf')}
    resp = client.post('/api/v1/summaries', files=files)
    assert resp.status_code == 200
    job_id = resp.json()['id']
    for _ in range(20):
        res = client.get(f'/api/v1/summaries/{job_id}')
        if res.json()['status'] == 'done':
            break
        time.sleep(0.1)
    data = res.json()
    assert data['status'] == 'done'
    assert 'Lay Summary' in data['payload']['summary']


def test_ref_summary(monkeypatch):
    def fake_fetch(ref: str):
        return 'Text from web about physics.', {'title': 'Phys Paper', 'authors': 'B'}
    monkeypatch.setattr(fetcher, 'fetch_and_extract', fake_fetch)
    resp = client.post('/api/v1/summaries', json={'ref': 'https://example.com/paper'})
    assert resp.status_code == 200
    job_id = resp.json()['id']
    for _ in range(20):
        res = client.get(f'/api/v1/summaries/{job_id}')
        if res.json()['status'] == 'done':
            break
        time.sleep(0.1)
    data = res.json()
    assert data['status'] == 'done'
    assert 'Lay Summary' in data['payload']['summary']


def test_singular_summary_route(monkeypatch):
    """Ensure /api/v1/summary/{id} works as an alias."""
    def fake_extract(path: str):
        return 'PDF content about chemistry.', {'title': 'Chem Paper', 'authors': 'C'}
    monkeypatch.setattr(pdfio, 'extract_text_and_meta', fake_extract)
    files = {'pdf': ('paper.pdf', b'fake', 'application/pdf')}
    resp = client.post('/api/v1/summary', files=files)
    assert resp.status_code == 200
    job_id = resp.json()['id']
    for _ in range(20):
        res = client.get(f'/api/v1/summary/{job_id}')
        if res.json()['status'] == 'done':
            break
        time.sleep(0.1)
    data = res.json()
    assert data['status'] == 'done'
    assert 'Lay Summary' in data['payload']['summary']


def test_crossref_fallback(monkeypatch):
    """Paywalled DOI falls back to Crossref abstract."""

    class DummyResp:
        def __init__(self, url: str, headers=None, text: str = "", json_data=None):
            self.url = url
            self.status_code = 200
            self.headers = headers or {}
            self._text = text
            self._json = json_data
            self.content = b""

        def raise_for_status(self):
            if self.status_code >= 400:
                raise fetcher.httpx.HTTPStatusError("err", request=None, response=self)

        def json(self):
            return self._json

        @property
        def text(self):
            return self._text

    class DummyClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def get(self, url):
            if url.startswith("https://api.crossref.org/works/"):
                data = {"message": {"abstract": "<jats:p>Crossref abstract text</jats:p>"}}
                return DummyResp(url, headers={"content-type": "application/json"}, json_data=data)
            # Simulate paywalled landing page with no text
            return DummyResp(url, headers={"content-type": "text/html"}, text="<html></html>")

    monkeypatch.setattr(fetcher.httpx, "Client", DummyClient)
    monkeypatch.setattr(fetcher.httpx, "Timeout", lambda *a, **k: None)

    captured = {}

    def fake_summarise(text, meta, length, system_prompt):
        captured['text'] = text
        return 'summary'

    monkeypatch.setattr(main.summarizer, 'summarise', fake_summarise)

    resp = client.post('/api/v1/summaries', json={'ref': '10.1234/paywalled'})
    assert resp.status_code == 200
    job_id = resp.json()['id']
    for _ in range(20):
        res = client.get(f'/api/v1/summaries/{job_id}')
        if res.json()['status'] == 'done':
            break
        time.sleep(0.1)
    data = res.json()
    assert data['status'] == 'done'
    assert data['payload']['meta']['source'] == 'crossref_abstract'
    assert captured['text'] == 'Crossref abstract text'
