from __future__ import annotations


def append_prompt_text(prompt: str, extra_text: str) -> str:
    prompt = (prompt or "").strip()
    extra = (extra_text or "").strip()
    if not extra:
        return prompt
    if not prompt:
        return extra
    return f"{prompt}\n\n{extra}"
