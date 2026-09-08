"""
DeepInfra implementation of InferenceProvider.

Uses DeepInfra's OpenAI-images-compatible endpoint:
POST {base_url}/images/generations
{
    "model": "black-forest-labs/FLUX-2-max",
    "prompt": "...",
    "n": 1,
    "size": "1024x1024",
    "response_format": "b64_json"
}
-> {"data": [{"b64_json": "..."}], ...}

Text-to-image only for now — no image/reference input.
"""
import asyncio
import base64
import logging

import httpx

from app.core.config import Settings
from app.inference.base import GeneratedImage, InferenceError, InferenceProvider

logger = logging.getLogger(__name__)


class DeepInfraProvider(InferenceProvider):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._price_by_model = {
            settings.DRAFT_MODEL: settings.DRAFT_PRICE_PER_IMAGE_USD,
            settings.FINAL_MODEL: settings.FINAL_PRICE_PER_IMAGE_USD,
        }

    async def generate(self, *, prompt: str, model: str, size: str) -> GeneratedImage:
        settings = self._settings
        url = f"{settings.DEEPINFRA_BASE_URL}/images/generations"
        headers = {
            "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json",
        }

        last_error: Exception | None = None
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                    resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code == 429:
                    # Rate limited — always worth retrying with backoff.
                    raise InferenceError(f"DeepInfra rate limited (attempt {attempt})", retryable=True)
                if resp.status_code >= 500:
                    raise InferenceError(f"DeepInfra server error {resp.status_code}", retryable=True)
                if resp.status_code >= 400:
                    # Bad request (bad prompt, bad model name, auth) — retrying won't help.
                    raise InferenceError(
                        f"DeepInfra rejected request ({resp.status_code}): {resp.text[:300]}",
                        retryable=False,
                    )

                data = resp.json()
                items = data.get("data") or []
                if not items or "b64_json" not in items[0]:
                    raise InferenceError(f"Unexpected DeepInfra response shape: {data}", retryable=False)

                image_bytes = base64.b64decode(items[0]["b64_json"])
                return GeneratedImage(
                    content=image_bytes,
                    content_type="image/png",
                    provider="deepinfra",
                    model=model,
                    cost_usd=self._price_by_model.get(model, 0.0),
                )

            except InferenceError as e:
                last_error = e
                if not e.retryable or attempt == settings.MAX_RETRIES:
                    raise
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_error = e
                if attempt == settings.MAX_RETRIES:
                    raise InferenceError(f"DeepInfra request failed after retries: {e}", retryable=True) from e

            backoff = settings.RETRY_BACKOFF_SECONDS * attempt
            logger.warning("DeepInfra call failed (attempt %s/%s): %s — retrying in %.1fs",
                           attempt, settings.MAX_RETRIES, last_error, backoff)
            await asyncio.sleep(backoff)

        # Should be unreachable, but keep mypy/pyright happy.
        raise InferenceError(f"DeepInfra call failed: {last_error}", retryable=False)


def get_provider(settings: Settings) -> InferenceProvider:
    if settings.INFERENCE_PROVIDER == "deepinfra":
        return DeepInfraProvider(settings)
    raise ValueError(f"Unknown INFERENCE_PROVIDER: {settings.INFERENCE_PROVIDER}")
