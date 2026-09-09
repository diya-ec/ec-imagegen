"""
Replicate implementation of InferenceProvider — image-to-image restyling
via Flux Kontext Pro. Takes an uploaded merchant photo + prompt, returns
a professionally restyled version. Mirrors the polling/retry pattern
validated in the test script.
"""
import asyncio
import io
import logging
import time

import replicate

from app.core.config import Settings
from app.inference.base import GeneratedImage, InferenceError, InferenceProvider

logger = logging.getLogger(__name__)


class ReplicateRestyleProvider(InferenceProvider):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)

    async def generate(
        self,
        *,
        prompt: str,
        model: str,
        size: str,
        input_image: bytes | None = None,
    ) -> GeneratedImage:
        if input_image is None:
            raise InferenceError("ReplicateRestyleProvider requires input_image", retryable=False)

        # replicate's SDK is sync — run it in a thread so the async worker path
        # (asyncio.run in worker.py) doesn't block the event loop unnecessarily.
        return await asyncio.to_thread(self._generate_sync, prompt, model, input_image)

    def _generate_sync(self, prompt: str, model: str, input_image: bytes) -> GeneratedImage:
        settings = self._settings
        last_err: Exception | None = None

        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                prediction = self._client.predictions.create(
                    model=model,
                    input={
                        "prompt": prompt,
                        "input_image": io.BytesIO(input_image),
                        "output_format": "jpg",
                    },
                )

                poll_start = time.time()
                while prediction.status not in ("succeeded", "failed", "canceled"):
                    if time.time() - poll_start > settings.RESTYLE_POLL_TIMEOUT_SECONDS:
                        raise InferenceError(
                            f"Replicate prediction {prediction.id} timed out "
                            f"(last status: {prediction.status})",
                            retryable=True,
                        )
                    time.sleep(3)
                    prediction.reload()

                if prediction.status == "failed":
                    raise InferenceError(f"Replicate prediction failed: {prediction.error}", retryable=True)
                if prediction.status == "canceled":
                    raise InferenceError("Replicate prediction was canceled", retryable=True)

                output = prediction.output
                file_obj = output[0] if isinstance(output, list) else output
                image_bytes = file_obj.read() if hasattr(file_obj, "read") else self._download(str(file_obj))

                return GeneratedImage(
                    content=image_bytes,
                    content_type="image/jpeg",
                    provider="replicate",
                    model=model,
                    cost_usd=settings.RESTYLE_PRICE_PER_IMAGE_USD,
                )

            except InferenceError as e:
                last_err = e
                if not e.retryable or attempt == settings.MAX_RETRIES:
                    raise
            except Exception as e:
                last_err = e
                if attempt == settings.MAX_RETRIES:
                    raise InferenceError(f"Replicate call failed after retries: {e}", retryable=True) from e

            backoff = settings.RETRY_BACKOFF_SECONDS * attempt
            logger.warning("Replicate call failed (attempt %s/%s): %s — retrying in %.1fs",
                           attempt, settings.MAX_RETRIES, last_err, backoff)
            time.sleep(backoff)

        raise InferenceError(f"Replicate call failed: {last_err}", retryable=False)

    @staticmethod
    def _download(url: str) -> bytes:
        import requests
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content


def get_restyle_provider(settings: Settings) -> InferenceProvider:
    return ReplicateRestyleProvider(settings)