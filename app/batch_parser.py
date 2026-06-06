from __future__ import annotations

import json
import re
import csv
from dataclasses import dataclass
from io import StringIO
from typing import List, Tuple, Optional


@dataclass
class BatchParseResult:
    prompts: List[str]
    errors: List[str]


def parse_batch_input(
    raw: str, mode: str = "lines", prompt_field: str = "prompt", csv_column: Optional[str] = None
) -> BatchParseResult:
    raw = raw.strip()
    if not raw:
        return BatchParseResult(prompts=[], errors=["Input is empty"])
    if mode == "lines":
        prompts = [line.strip() for line in raw.splitlines() if line.strip()]
        return BatchParseResult(prompts=prompts, errors=[])
    if mode == "numbered":
        prompts: List[str] = []
        errors: List[str] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            match = re.match(r"^\s*\d+\s*[\.\)\-]\s*(.+)$", line)
            if match:
                prompts.append(match.group(1).strip())
            else:
                errors.append(f"Could not parse numbered line: {line}")
        return BatchParseResult(prompts=prompts, errors=errors)
    if mode == "json_array":
        try:
            data = json.loads(raw)
        except Exception as exc:
            return BatchParseResult(prompts=[], errors=[f"JSON error: {exc}"])
        prompts = []
        errors: List[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    prompts.append(item)
                elif isinstance(item, dict) and prompt_field in item:
                    prompts.append(str(item[prompt_field]))
                else:
                    errors.append(f"Unsupported item: {item}")
        else:
            errors.append("JSON array expected")
        return BatchParseResult(prompts=prompts, errors=errors)
    if mode == "json_lines":
        prompts: List[str] = []
        errors: List[str] = []
        for idx, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as exc:
                errors.append(f"Line {idx}: {exc}")
                continue
            if isinstance(obj, dict) and prompt_field in obj:
                prompts.append(str(obj[prompt_field]))
            else:
                errors.append(f"Line {idx}: missing '{prompt_field}'")
        return BatchParseResult(prompts=prompts, errors=errors)
    if mode == "csv":
        prompts: List[str] = []
        errors: List[str] = []
        try:
            reader = csv.reader(StringIO(raw))
            rows = list(reader)
            if not rows:
                return BatchParseResult([], ["CSV empty"])
            headers = rows[0]
            has_header = bool(headers) and (csv_column is None or not csv_column.isdigit())
            body = rows[1:] if has_header else rows
            col_idx = None
            if headers and csv_column:
                if csv_column.isdigit():
                    col_idx = int(csv_column)
                elif csv_column in headers:
                    col_idx = headers.index(csv_column)
            if col_idx is None:
                col_idx = 0
            for idx, row in enumerate(body, start=1):
                if col_idx >= len(row):
                    errors.append(f"Line {idx}: column {col_idx} missing")
                    continue
                value = row[col_idx].strip()
                if value:
                    prompts.append(value)
        except Exception as exc:
            errors.append(f"CSV parse error: {exc}")
        return BatchParseResult(prompts=prompts, errors=errors)
    return BatchParseResult(prompts=[], errors=[f"Unknown mode {mode}"])
