from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings


class StorageBackend(ABC):
    @abstractmethod
    def save(self, *, key: str, content: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def read(self, path: str) -> bytes:
        """Read back bytes previously saved at `path` (as returned by save())."""
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

    def read(self, path: str) -> bytes:
        return Path(path).read_bytes()


class S3Storage(StorageBackend):
    def __init__(self, bucket: str, region: str):
        self._bucket = bucket
        self._region = region

    def save(self, *, key: str, content: bytes) -> str:
        raise NotImplementedError("S3Storage not wired up yet — set STORAGE_BACKEND=local for now.")

    def read(self, path: str) -> bytes:
        raise NotImplementedError("S3Storage not wired up yet — set STORAGE_BACKEND=local for now.")


def get_storage(settings: Settings) -> StorageBackend:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorage(settings.LOCAL_STORAGE_DIR)
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage(settings.S3_BUCKET, settings.S3_REGION)
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND}")
