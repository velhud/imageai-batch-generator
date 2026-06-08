from __future__ import annotations

import base64
import os
import random
import time
from pathlib import Path
from threading import Event
from typing import Any, Dict, List

from app.models import DEFAULT_SIZE_PRESETS, GeneratedImage, GenerationContext, GlobalSettings, ModelInfo, ProviderCapabilities
from .base import BaseProvider, ProviderFilteredError, ProviderRetryExhaustedError, ProviderGenerationError


AZURE_PROVIDER_ID = "azure-openai"
AZURE_GPT_IMAGE_2_MODEL_ID = "gpt-image-2"
TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class AzureOpenAIImageProvider(BaseProvider):
    id = AZURE_PROVIDER_ID
    name = "Azure OpenAI"

    def __init__(self) -> None:
        capabilities = ProviderCapabilities(
            max_images=10,
            supports_style=False,
            supports_negative_prompt=False,
            supports_seed=False,
            supports_quality=True,
            supports_safety=False,
            size_presets=dict(DEFAULT_SIZE_PRESETS),
        )
        model = ModelInfo(
            id=AZURE_GPT_IMAGE_2_MODEL_ID,
            name="GPT-Image-2",
            provider_id=self.id,
            capabilities=capabilities,
        )
        super().__init__(
            [model],
            rate_limit_note="Azure GPT-Image-2 defaults: 5 images/min/deployment; start at 4/min, concurrency 1.",
        )

    def quota_cost(self, settings: GlobalSettings) -> int:
        return max(1, min(int(settings.num_images or 1), 10))

    def generate_images(
        self,
        prompt: str,
        settings: GlobalSettings,
        output_dir: Path,
        cancel_event: Event,
        attachments: List[object] = [],
        context: GenerationContext | None = None,
    ) -> List[GeneratedImage]:
        config = self._load_config()
        if cancel_event.is_set():
            raise RuntimeError("Cancelled")

        try:
            import requests  # type: ignore
        except Exception as exc:  # pragma: no cover - import-time guard
            raise RuntimeError(f"requests package not available: {exc}") from exc

        output_dir.mkdir(parents=True, exist_ok=True)
        payload = self.build_payload(prompt, settings, config["deployment"])
        url = self.build_url(config["endpoint"], config["api_version"])
        headers = {"Content-Type": "application/json", "api-key": config["api_key"]}

        last_metadata: Dict[str, Any] = {}
        for attempt in range(1, 6):
            if cancel_event.is_set():
                raise RuntimeError("Cancelled")
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=180)
            except requests.RequestException as exc:  # pragma: no cover - network runtime
                last_metadata = {"attempt": attempt, "error": str(exc)}
                if attempt == 5:
                    raise ProviderRetryExhaustedError(f"Azure request retry exhausted: {exc}", metadata=last_metadata) from exc
                self._sleep_before_retry(attempt)
                continue

            request_id = self._request_id(response)
            last_metadata = {
                "attempt": attempt,
                "azure_request_id": request_id,
                "http_status": response.status_code,
            }

            if response.status_code == 200:
                return self._write_images(response.json(), output_dir, settings, context, request_id, attempt, config["deployment"])

            error_text = response.text
            last_metadata["error"] = error_text[:2000]
            if self._is_content_filter_error(error_text, response.status_code):
                raise ProviderFilteredError("Azure content filter blocked this prompt.", metadata=last_metadata)

            if response.status_code in TRANSIENT_STATUSES:
                if attempt == 5:
                    raise ProviderRetryExhaustedError(
                        f"Azure transient error retry exhausted: {response.status_code}",
                        metadata=last_metadata,
                    )
                self._sleep_before_retry(attempt)
                continue

            raise ProviderGenerationError(
                f"Azure error {response.status_code}: {error_text[:500]}",
                metadata=last_metadata,
            )

        raise ProviderRetryExhaustedError("Azure retry exhausted.", metadata=last_metadata)

    def build_url(self, endpoint: str, api_version: str) -> str:
        return f"{endpoint.rstrip('/')}/openai/v1/images/generations?api-version={api_version}"

    def build_payload(self, prompt: str, settings: GlobalSettings, deployment: str) -> Dict[str, Any]:
        return {
            "model": deployment,
            "prompt": prompt,
            "size": self._size_string(settings),
            "quality": self.quality_from_setting(settings.quality),
            "n": max(1, min(int(settings.num_images or 1), 10)),
            "output_format": "png",
        }

    def quality_from_setting(self, value: int | None) -> str:
        value = int(value or 5)
        if value <= 3:
            return "low"
        if value >= 8:
            return "high"
        return "medium"

    def _load_config(self) -> Dict[str, str]:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
        deployment = os.environ.get("AZURE_GPT_IMAGE_2_DEPLOYMENT", "").strip()
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "preview").strip() or "preview"
        missing = [
            name
            for name, value in {
                "AZURE_OPENAI_ENDPOINT": endpoint,
                "AZURE_OPENAI_API_KEY": api_key,
                "AZURE_GPT_IMAGE_2_DEPLOYMENT": deployment,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing Azure OpenAI configuration: {', '.join(missing)}")
        return {
            "endpoint": endpoint,
            "api_key": api_key,
            "deployment": deployment,
            "api_version": api_version,
        }

    def _write_images(
        self,
        payload: Dict[str, Any],
        output_dir: Path,
        settings: GlobalSettings,
        context: GenerationContext | None,
        request_id: str,
        attempt: int,
        deployment: str,
    ) -> List[GeneratedImage]:
        data = payload.get("data") or []
        if not data:
            raise ProviderGenerationError("Azure did not return image data.", metadata={"azure_request_id": request_id})

        quality = self.quality_from_setting(settings.quality)
        results: List[GeneratedImage] = []
        for idx, image_data in enumerate(data):
            b64_json = image_data.get("b64_json")
            if not b64_json:
                continue
            file_name = self._output_filename(context, quality, idx)
            path = output_dir / file_name
            path.write_bytes(base64.b64decode(b64_json))
            results.append(
                GeneratedImage(
                    file_path=path,
                    metadata={
                        "provider": self.id,
                        "model": AZURE_GPT_IMAGE_2_MODEL_ID,
                        "deployment": deployment,
                        "size": self._size_string(settings),
                        "quality": quality,
                        "n": max(1, min(int(settings.num_images or 1), 10)),
                        "output_format": "png",
                        "attempt": attempt,
                        "azure_request_id": request_id,
                    },
                )
            )

        if not results:
            raise ProviderGenerationError("Azure response contained no decodable images.", metadata={"azure_request_id": request_id})
        return results

    def _output_filename(self, context: GenerationContext | None, quality: str, response_index: int) -> str:
        category_id = self._safe_token(context.category_id if context else "cat00", "cat00")
        prompt_id = self._safe_token(context.prompt_id if context else "prompt0001", "prompt0001")
        run_index = (context.run_index if context else 1) + response_index
        return f"{category_id}_{prompt_id}_q-{quality}_run{run_index:02d}.png"

    def _size_string(self, settings: GlobalSettings) -> str:
        if settings.custom_size:
            width = int(settings.custom_size.get("width", 1024) or 1024)
            height = int(settings.custom_size.get("height", 1024) or 1024)
            return f"{width}x{height}"
        preset = DEFAULT_SIZE_PRESETS.get(settings.size_preset or "", DEFAULT_SIZE_PRESETS["Square 1024"])
        return f"{preset.get('width', 1024)}x{preset.get('height', 1024)}"

    def _safe_token(self, value: str | None, fallback: str) -> str:
        value = (value or fallback).strip() or fallback
        return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value)

    def _request_id(self, response: Any) -> str:
        return response.headers.get("x-request-id") or response.headers.get("apim-request-id") or ""

    def _is_content_filter_error(self, error_text: str, status_code: int) -> bool:
        lowered = error_text.lower()
        return status_code in {400, 403} and any(
            marker in lowered for marker in ("contentfilter", "content_filter", "content policy", "content_policy", "filtered")
        )

    def _sleep_before_retry(self, attempt: int) -> None:
        sleep_s = min(240, 15 * (2 ** (attempt - 1))) + random.uniform(0, 5)
        time.sleep(sleep_s)
