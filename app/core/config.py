"""
Centralized settings. Everything that might change between local dev,
staging, and prod (or when we later swap DeepInfra for a self-hosted
fine-tuned model) lives here — never hardcode it in services/routers.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Inference provider ---
    # "deepinfra" today; add "self_hosted" later without touching callers.
    INFERENCE_PROVIDER: str = "deepinfra"
    DEEPINFRA_API_KEY: str = ""
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"

    # Model identifiers used for draft (cheap/fast) vs final (flagship) renders.
    DRAFT_MODEL: str = "black-forest-labs/FLUX-2-klein"
    FINAL_MODEL: str = "black-forest-labs/FLUX-2-max"

    # Per-image pricing, used purely for cost logging/analytics — not billing math.
    DRAFT_PRICE_PER_IMAGE_USD: float = 0.014
    FINAL_PRICE_PER_IMAGE_USD: float = 0.07

    # --- Wizard / regen policy (hybrid draft-then-final strategy) ---
    MAX_DRAFT_VARIATIONS: int = 3       # cheap previews per item, essentially "free" to retry
    MAX_FINAL_REGENS: int = 1           # safety-valve retries on the flagship render, same prompt/new seed
    IMAGE_SIZE: str = "1024x1024"

    # --- Storage (local disk for now; swap for S3 client later) ---
    STORAGE_BACKEND: str = "local"      # "local" | "s3"
    LOCAL_STORAGE_DIR: str = "./storage"
    S3_BUCKET: str = ""
    S3_REGION: str = ""

    # --- DB / queue ---
    DATABASE_URL: str = "postgresql+psycopg://ecimagegen:ecimagegen@localhost:5432/ecimagegen"
    REDIS_URL: str = "redis://localhost:6379/0"
    RQ_QUEUE_NAME: str = "imagegen"

    # --- HTTP behavior towards the inference API ---
    REQUEST_TIMEOUT_SECONDS: int = 60
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
