from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        extra="ignore",
    )

    # --- Inference provider (image-to-image restyle only) ---
    REPLICATE_API_TOKEN: str = ""
    RESTYLE_MODEL: str = "black-forest-labs/flux-kontext-pro"
    RESTYLE_PRICE_PER_IMAGE_USD: float = 0.04  # check Replicate's actual per-run price
    RESTYLE_POLL_TIMEOUT_SECONDS: int = 180

    # --- Upload validation ---
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_UPLOAD_CONTENT_TYPES: set[str] = {
        "image/jpeg", "image/png", "image/webp", "image/heic", "image/jpg",
    }

    # How many restyle variations to generate per upload, so the merchant can
    # pick a favorite. Each variation is a separate ImageJob (same batch_id,
    # same source_image_path) with a rotated style directive from
    # prompt_builder.RESTYLE_VARIATION_STYLES.
    MAX_RESTYLE_VARIATIONS: int = 3

    IMAGE_SIZE: str = "1024x1024"

    # --- Storage (local disk for now; swap for S3 client later) ---
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = str(_PROJECT_ROOT / "storage")
    S3_BUCKET: str = ""
    S3_REGION: str = ""

    # --- DB / queue ---
    DATABASE_URL: str = "postgresql+psycopg://postgres:Mitesh%40123@localhost:5432/ecimagegen"
    REDIS_URL: str = "redis://localhost:6379/0"
    RQ_QUEUE_NAME: str = "imagegen"

    # --- HTTP behavior towards the inference API ---
    REQUEST_TIMEOUT_SECONDS: int = 60
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: float = 2.0

    # RQ's default job_timeout (180s) is too short for restyle jobs, which can
    # legitimately take several minutes (poll timeout + retries). Used at
    # enqueue time in job_service.py.
    RESTYLE_JOB_TIMEOUT_SECONDS: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()