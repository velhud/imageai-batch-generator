from __future__ import annotations

import base64
import os
from pathlib import Path
from threading import Event
from typing import List

from app.models import GlobalSettings, ModelInfo, ProviderCapabilities
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    id = "openai"
    name = "OpenAI"

    def __init__(self) -> None:
        capabilities = ProviderCapabilities(
            max_images=4,
            supports_style=True,
            supports_negative_prompt=False,
            supports_seed=False,
            supports_quality=True,
            supports_safety=False,
        )
        model = ModelInfo(
            id="dall-e-3",
            name="DALL·E 3",
            provider_id=self.id,
            capabilities=capabilities,
        )
        super().__init__([model], rate_limit_note="OpenAI shared rate limits apply.")

    def generate_images(
        self,
        prompt: str,
        settings: GlobalSettings,
        output_dir: Path,
        cancel_event: Event,
        attachments: List[object] = [],
    ) -> List[Path]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY for OpenAI provider.")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - import-time guard
            raise RuntimeError(f"openai package not available: {exc}") from exc

        client = OpenAI(api_key=api_key)
        size = settings.custom_size or {"width": 1024, "height": 1024}
        size_string = f"{size.get('width', 1024)}x{size.get('height', 1024)}"

        count = max(1, min(settings.num_images, 4))
        if cancel_event.is_set():
            raise RuntimeError("Cancelled")

        response = client.images.generate(
            model=settings.model_id or "dall-e-3",
            prompt=prompt,
            size=size_string,
            quality="high" if settings.quality and settings.quality >= 7 else "standard",
            n=count,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        paths: List[Path] = []
        for idx, img_data in enumerate(response.data):
            if cancel_event.is_set():
                break
            if img_data.b64_json:
                raw = base64.b64decode(img_data.b64_json)
                path = output_dir / f"openai_{idx}.png"
                with open(path, "wb") as f:
                    f.write(raw)
                paths.append(path)
        return paths
