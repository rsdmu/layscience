import os
import sys
import time
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Ensure DRY_RUN for tests
os.environ['DRY_RUN'] = '1'

from backend.server import main
from backend.server.services import pdfio, fetcher

client = TestClient(main.app)

multipart_installed = importlib.util.find_spec('multipart') is not None


def test_start_summary_missing_input():
    resp = client.post('/api/v1/summaries', json={})
    assert resp.status_code == 400
    body = resp.json()
    assert body['error'] == 'missing_input'


@pytest.mark.skipif(not multipart_installed, reason='python-multipart not installed')
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


@pytest.mark.skipif(not multipart_installed, reason='python-multipart not installed')
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


def test_ref_summary_real_fetch(monkeypatch, tmp_path):
    """Ensure real fetches keep HTTPX clients open for follow-up requests."""
    import threading
    import http.server
    import socketserver
    from functools import partial

    # Prepare a tiny site with an HTML page linking to a PDF
    (tmp_path / 'index.html').write_text('<a href="paper.pdf">pdf</a>')
    (tmp_path / 'paper.pdf').write_bytes(b'%PDF-1.4 fake')

    # Stub PDF extraction
    def fake_extract(path: str):
        return 'PDF text', {'title': 'Local PDF'}

    monkeypatch.setattr(pdfio, 'extract_text_and_meta', fake_extract)
    monkeypatch.setattr(fetcher, 'extract_text_and_meta', fake_extract)

    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    httpd = socketserver.TCPServer(('localhost', 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        resp = client.post('/api/v1/summaries', json={'ref': f'http://localhost:{port}/index.html'})
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
    finally:
        httpd.shutdown()
