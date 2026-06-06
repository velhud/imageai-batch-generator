from app.models import SessionData, GlobalSettings, RowData
from app.undo_manager import UndoManager


def test_undo_redo_roundtrip():
    session = SessionData(id="1", global_settings=GlobalSettings(), rows=[])
    mgr = UndoManager()
    mgr.push(session)
    session.rows.append(RowData(id="r1"))
    undoed = mgr.undo()
    assert isinstance(undoed, SessionData)
    redone = mgr.redo()
    assert isinstance(redone, SessionData)
