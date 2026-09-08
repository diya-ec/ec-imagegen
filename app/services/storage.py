from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings


class StorageBackend(ABC):
    @abstractmethod
    def save(self, *, key: str, content: bytes) -> str:
        """Persist bytes under `key`, return a path/URL usable to retrieve it later."""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: str):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, key: str, content: bytes) -> str:
        path = self._base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)


class S3Storage(StorageBackend):
    """Placeholder — wire up boto3 here when moving off local disk."""
    def __init__(self, bucket: str, region: str):
        self._bucket = bucket
        self._region = region

    def save(self, *, key: str, content: bytes) -> str:
        raise NotImplementedError("S3Storage not wired up yet — set STORAGE_BACKEND=local for now.")


def get_storage(settings: Settings) -> StorageBackend:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorage(settings.LOCAL_STORAGE_DIR)
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage(settings.S3_BUCKET, settings.S3_REGION)
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND}")
