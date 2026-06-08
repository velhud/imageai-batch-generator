from pathlib import Path

from app.session_manager import SessionManager
from app.models import GlobalSettings, RowData


def test_session_save_load(tmp_path: Path):
    mgr = SessionManager()
    mgr.add_rows(["a", "b"])
    path = tmp_path / "session.json"
    mgr.save(path)
    assert path.exists()
    loaded = mgr.load(path)
    assert len(loaded.rows) == 2
    assert loaded.rows[0].prompt == "a"


def test_old_row_data_defaults_new_batch_metadata():
    row = RowData.from_dict({"id": "row1", "prompt": "legacy prompt", "status": "Idle", "settings": {}})
    assert row.prompt_id == ""
    assert row.category_id == ""
    assert row.source_metadata == {}


def test_old_global_settings_defaults_prompt_wrapper():
    settings = GlobalSettings.from_dict({})
    assert settings.prompt_wrapper == ""
