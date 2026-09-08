import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobStage(str, enum.Enum):
    DRAFT = "draft"
    FINAL = "final"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageJob(Base):
    """
    One row per generated image.

    batch_id groups everything that came from a single wizard submission for
    one menu item: MAX_DRAFT_VARIATIONS draft rows, plus (once the merchant
    picks one) a FINAL row. Regenerating the final creates a new FINAL row
    with the same batch_id and an incremented regen_count, rather than
    mutating the old one — keeps a full audit trail per item.
    """
    __tablename__ = "image_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), default=_uuid, index=True)

    restaurant_id: Mapped[str] = mapped_column(String(64), index=True)
    menu_item_id: Mapped[str] = mapped_column(String(64), index=True)

    stage: Mapped[JobStage] = mapped_column(Enum(JobStage), index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING, index=True)

    prompt: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Only meaningful for FINAL jobs — how many flagship regens this batch has used.
    regen_count: Mapped[int] = mapped_column(Integer, default=0)

    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
