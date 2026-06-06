from __future__ import annotations

from typing import List

from app.models import RowData


def has_tags(row: RowData, tags: List[str]) -> bool:
    if not tags:
        return True
    row_tags = set(t.lower() for t in row.tags)
    return all(t.lower() in row_tags for t in tags)


def filter_rows(rows: List[RowData], tags: List[str]) -> List[RowData]:
    return [r for r in rows if has_tags(r, tags)]
