import importlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import backend.server.main as main_module
from backend.server.services import accounts_db


def test_accounts_db_init_failure_falls_back(monkeypatch, tmp_path):
    """If the PostgreSQL connection fails we fall back to JSON storage."""
    # Start from a clean environment/state.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    accounts_db.engine = None
    importlib.reload(main_module)

    data_dir = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/db")

    calls = {}

    def failing_init():
        calls["init"] = True
        raise RuntimeError("boom")

    monkeypatch.setattr(accounts_db, "init", failing_init)

    reloaded = importlib.reload(main_module)

    assert calls.get("init") is True
    assert reloaded.DATABASE_URL is None
    assert reloaded.accounts == {}
    assert reloaded.pending_codes == {}

    # Clean up by restoring environment and module state for subsequent tests.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    accounts_db.engine = None
    importlib.reload(main_module)
