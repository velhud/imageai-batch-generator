from pathlib import Path

from app.session_manager import SessionManager


def test_session_save_load(tmp_path: Path):
    mgr = SessionManager()
    mgr.add_rows(["a", "b"])
    path = tmp_path / "session.json"
    mgr.save(path)
    assert path.exists()
    loaded = mgr.load(path)
    assert len(loaded.rows) == 2
    assert loaded.rows[0].prompt == "a"
