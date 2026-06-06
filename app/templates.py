from __future__ import annotations

import itertools
from typing import Dict, List

from app.models import PromptTemplate


def expand_template(template: PromptTemplate) -> List[str]:
    """Expand template by cartesian product of variable values."""
    keys = list(template.variables.keys())
    if not keys:
        return [template.template]
    values_lists = [template.variables[k] for k in keys]
    prompts: List[str] = []
    for combo in itertools.product(*values_lists):
        filled = template.template
        for key, val in zip(keys, combo):
            filled = filled.replace("{" + key + "}", str(val))
        prompts.append(filled)
    return prompts


def parse_variable_block(block: str) -> Dict[str, List[str]]:
    """Parse simple block of lines 'key: a, b, c' into variable dict."""
    variables: Dict[str, List[str]] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, vals = line.split(":", 1)
        variables[key.strip()] = [v.strip() for v in vals.split(",") if v.strip()]
    return variables
