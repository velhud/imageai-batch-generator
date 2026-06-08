from pathlib import Path

from app.generation_log import verify_rows
from app.models import ImageResult, RowData, RowStatus


def test_verify_rows_detects_success_filtered_failed_and_missing(tmp_path: Path):
    image = tmp_path / "cat01_prompt0001_q-medium_run01.png"
    image.write_bytes(b"png")
    rows = [
        RowData(
            id="row1",
            prompt="one",
            prompt_id="prompt0001",
            status=RowStatus.COMPLETED,
            images=[ImageResult(id="img1", row_id="row1", file_path=str(image))],
        ),
        RowData(id="row2", prompt="two", prompt_id="prompt0002", status=RowStatus.FILTERED),
        RowData(id="row3", prompt="three", prompt_id="prompt0003", status=RowStatus.ERROR),
        RowData(id="row4", prompt="four", prompt_id="prompt0004", status=RowStatus.IDLE),
    ]

    result = verify_rows(rows)

    assert result["successful_images"] == 1
    assert result["filtered_prompt_ids"] == ["prompt0002"]
    assert result["failed_prompt_ids"] == ["prompt0003"]
    assert result["missing_prompt_ids"] == ["prompt0004"]
    assert not result["matches_prompt_count"]
