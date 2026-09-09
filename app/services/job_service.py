import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ImageJob, JobStage, JobStatus
from app.queue import image_queue
from app.schemas import CreateDraftBatchRequest
from app.services.prompt_builder import build_prompt, build_restyle_prompt
from app.services.storage import get_storage
from app.worker import process_image_job

settings = get_settings()


class RegenLimitExceeded(Exception):
    pass


class DraftNotFound(Exception):
    pass


def create_draft_batch(db: Session, req: CreateDraftBatchRequest) -> list[ImageJob]:
    """Kick off MAX_DRAFT_VARIATIONS cheap preview renders for one wizard submission."""
    prompt = build_prompt(req.wizard_answers)
    batch_id = str(uuid.uuid4())

    jobs: list[ImageJob] = []
    for _ in range(settings.MAX_DRAFT_VARIATIONS):
        job = ImageJob(
            batch_id=batch_id,
            restaurant_id=req.restaurant_id,
            menu_item_id=req.menu_item_id,
            stage=JobStage.DRAFT,
            status=JobStatus.PENDING,
            prompt=prompt,
        )
        db.add(job)
        jobs.append(job)

    db.commit()
    for job in jobs:
        db.refresh(job)
        image_queue.enqueue(process_image_job, job.id)

    return jobs

def create_restyle_job(
    db: Session,
    *,
    restaurant_id: str | None,
    menu_item_id: str | None,
    extra_styling: str | None,
    photo_bytes: bytes,
    photo_filename: str,
) -> ImageJob:
    storage = get_storage(settings)
    batch_id = str(uuid.uuid4())

    rid = restaurant_id or "unknown"
    mid = menu_item_id or "unknown"

    source_key = f"{rid}/{mid}/{batch_id}/source_{photo_filename}"
    source_path = storage.save(key=source_key, content=photo_bytes)

    prompt = build_restyle_prompt(extra_styling)

    job = ImageJob(
        batch_id=batch_id,
        restaurant_id=rid,
        menu_item_id=mid,
        stage=JobStage.RESTYLE,
        status=JobStatus.PENDING,
        prompt=prompt,
        source_image_path=source_path,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    image_queue.enqueue(process_image_job, job.id)
    return job

def select_draft(db: Session, draft_job_id: int) -> ImageJob:
    """Merchant picked a draft — render the same prompt on the flagship model."""
    draft = db.get(ImageJob, draft_job_id)
    if draft is None or draft.stage != JobStage.DRAFT:
        raise DraftNotFound(f"No draft job with id {draft_job_id}")

    final_job = ImageJob(
        batch_id=draft.batch_id,
        restaurant_id=draft.restaurant_id,
        menu_item_id=draft.menu_item_id,
        stage=JobStage.FINAL,
        status=JobStatus.PENDING,
        prompt=draft.prompt,
        regen_count=0,
    )
    db.add(final_job)
    db.commit()
    db.refresh(final_job)

    image_queue.enqueue(process_image_job, final_job.id)
    return final_job


def regenerate_final(db: Session, batch_id: str) -> ImageJob:
    """
    Safety-valve retry on the flagship model itself (same prompt, new seed via
    a fresh generation call) — capped at MAX_FINAL_REGENS so a merchant can't
    rack up unbounded flagship-priced attempts.
    """
    latest_final = (
        db.query(ImageJob)
        .filter(ImageJob.batch_id == batch_id, ImageJob.stage == JobStage.FINAL)
        .order_by(ImageJob.regen_count.desc())
        .first()
    )
    if latest_final is None:
        raise DraftNotFound(f"No final job yet for batch {batch_id} — select a draft first")

    if latest_final.regen_count >= settings.MAX_FINAL_REGENS:
        raise RegenLimitExceeded(
            f"Batch {batch_id} has used its {settings.MAX_FINAL_REGENS} allowed flagship regen(s)"
        )

    new_final = ImageJob(
        batch_id=batch_id,
        restaurant_id=latest_final.restaurant_id,
        menu_item_id=latest_final.menu_item_id,
        stage=JobStage.FINAL,
        status=JobStatus.PENDING,
        prompt=latest_final.prompt,
        regen_count=latest_final.regen_count + 1,
    )
    db.add(new_final)
    db.commit()
    db.refresh(new_final)

    image_queue.enqueue(process_image_job, new_final.id)
    return new_final
