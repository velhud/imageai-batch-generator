from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_if_available() -> None:
    """
    Load a .env file from the project root if python-dotenv is installed.
    This keeps API keys (e.g., GEMINI_API_KEY, OPENAI_API_KEY) in a simple
    root-level .env without crashing when the dependency is missing.
    """
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        # Fallback: naive parser so we still pick up keys when python-dotenv isn't installed.
        try:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        except Exception:
            pass
        return

    load_dotenv(env_path, override=False)
