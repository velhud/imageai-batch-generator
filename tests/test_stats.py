from app.models import RowData, RowStatus, RowSettings
from app.stats import compute_stats


def test_stats_counts():
    r1 = RowData(id="1", prompt="a", status=RowStatus.COMPLETED, settings=RowSettings(provider_id="p1"))
    r2 = RowData(id="2", prompt="b", status=RowStatus.ERROR, settings=RowSettings(provider_id="p1"))
    stats = compute_stats([r1, r2])
    assert stats.total == 2
    assert stats.completed == 1
    assert stats.errors == 1
    assert stats.per_provider["p1"] == 2
