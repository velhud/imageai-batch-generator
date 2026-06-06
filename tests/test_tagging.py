from app.models import RowData
from app.tagging import filter_rows


def test_filter_rows_by_tag():
    r1 = RowData(id="1", prompt="a", tags=["cat", "cute"])
    r2 = RowData(id="2", prompt="b", tags=["dog"])
    filtered = filter_rows([r1, r2], ["cat"])
    assert filtered == [r1]
