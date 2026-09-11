"""
Inference provider interface.

This service is image-to-image restyle only. Every generation call goes
through this interface. Today the only implementation is Replicate (Flux
Kontext Pro). If another image-to-image provider is added later (e.g. a
self-hosted model), it implements this same interface and callers never
change.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GeneratedImage:
    content: bytes
    content_type: str  # e.g. "image/jpeg"
    provider: str
    model: str
    cost_usd: float


class InferenceProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        model: str,
        size: str,
        input_image: bytes,
    ) -> GeneratedImage:
        """Generate one restyled image from a source image + prompt."""
        raise NotImplementedError


class InferenceError(Exception):
    """Raised for any provider failure (HTTP error, timeout, bad response shape)."""
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable