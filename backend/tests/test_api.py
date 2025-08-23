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


def test_empty_content_message_includes_ref(monkeypatch):
    def fake_fetch(ref: str):
        return '', {}

    monkeypatch.setattr(fetcher, 'fetch_and_extract', fake_fetch)
    ref = 'https://example.com/paywalled'
    resp = client.post('/api/v1/summaries', json={'ref': ref})
    assert resp.status_code == 200
    job_id = resp.json()['id']
    for _ in range(20):
        res = client.get(f'/api/v1/jobs/{job_id}')
        data = res.json()
        if data['status'] == 'failed':
            break
        time.sleep(0.1)
    assert data['status'] == 'failed'
    assert data['error']['code'] == 'empty_content'
    assert ref in data['error']['message']
