from __future__ import annotations

from collections import Counter
from typing import List

from app.models import RowData, RowStatus, StatsSnapshot


def compute_stats(rows: List[RowData]) -> StatsSnapshot:
    total = len(rows)
    completed = len([r for r in rows if r.status == RowStatus.COMPLETED])
    errors = len([r for r in rows if r.status == RowStatus.ERROR])
    durations = [r.last_duration for r in rows if r.last_duration]
    avg_duration = sum(durations) / len(durations) if durations else 0.0
    per_provider = Counter(
        [r.settings.provider_id for r in rows if r.settings.provider_id]
    )
    per_model = Counter([r.settings.model_id for r in rows if r.settings.model_id])
    per_style = Counter([r.settings.style_preset for r in rows if r.settings.style_preset])
    return StatsSnapshot(
        total=total,
        completed=completed,
        errors=errors,
        average_duration=avg_duration,
        per_provider=dict(per_provider),
        per_model=dict(per_model),
        per_style=dict(per_style),
    )
