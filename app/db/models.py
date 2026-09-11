import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageJob(Base):
    """
    One row per generated image.

    This service is image-to-image restyle only: the merchant uploads one
    source photo, batch_id groups MAX_RESTYLE_VARIATIONS rows generated from
    that same photo (each with a different style directive), and the
    merchant picks their favorite. is_selected marks which variation was
    picked; unlike the old draft->final flow, picking a restyle variation
    does not trigger a re-render, since restyle output is already full
    quality. At most one row per batch_id should have is_selected=True
    (enforced in job_service, not the DB).
    """
    __tablename__ = "image_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), default=_uuid, index=True)

    restaurant_id: Mapped[str] = mapped_column(String(64), index=True)
    menu_item_id: Mapped[str] = mapped_column(String(64), index=True)

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING, index=True)

    prompt: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Path to the merchant's original upload — required, every job here is a restyle job.
    source_image_path: Mapped[str] = mapped_column(String(512))

    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)

    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)