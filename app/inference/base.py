"""
Inference provider interface.

Every model call in this system — draft or final — goes through this
interface. Today the only implementation is DeepInfra. When Donil's team
finishes fine-tuning a self-hosted model, they add a new class here
(e.g. SelfHostedProvider) and flip Settings.INFERENCE_PROVIDER — routers,
services, and the worker never change.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GeneratedImage:
    content: bytes
    content_type: str  # e.g. "image/png"
    provider: str
    model: str
    cost_usd: float


class InferenceProvider(ABC):
    @abstractmethod
    async def generate(self, *, prompt: str, model: str, size: str) -> GeneratedImage:
        """Generate a single text-to-image result. Raises InferenceError on failure."""
        raise NotImplementedError


class InferenceError(Exception):
    """Raised for any provider failure (HTTP error, timeout, bad response shape)."""
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable
