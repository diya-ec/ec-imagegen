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

# Replicate/Flux Kontext calls can legitimately take 30-90s+, plus our own
# retry loop (MAX_RETRIES attempts, each waiting up to RESTYLE_POLL_TIMEOUT_SECONDS)
# means worst case is several minutes. RQ's default job_timeout is 180s (3 min),
# which was killing restyle jobs mid-flight and leaving them stuck at
# PROCESSING (see worker.py's broad exception handling for the other half of
# this fix). Give restyle jobs a longer budget explicitly.
RESTYLE_JOB_TIMEOUT_SECONDS = 600  # 10 minutes


class RegenLimitExceeded(Exception):
    pass


class DraftNotFound(Exception):
    pass


class RestyleJobNotFound(Exception):
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


def create_restyle_batch(
    db: Session,
    *,
    restaurant_id: str | None,
    menu_item_id: str | None,
    extra_styling: str | None,
    photo_bytes: bytes,
    photo_filename: str,
) -> list[ImageJob]:
    """
    Merchant uploaded their own photo — restyle it via Flux Kontext Pro
    (Replicate) into MAX_RESTYLE_VARIATIONS distinct-looking options, mirroring
    create_draft_batch's "generate a few, let them pick" pattern. The source
    photo is uploaded and saved exactly once; every variation job in the batch
    points at the same source_image_path and only differs in its prompt (via a
    rotated style directive from prompt_builder) and, downstream, its
    generation result.
    """
    storage = get_storage(settings)
    batch_id = str(uuid.uuid4())

    rid = restaurant_id or "unknown"
    mid = menu_item_id or "unknown"

    source_key = f"{rid}/{mid}/{batch_id}/source_{photo_filename}"
    source_path = storage.save(key=source_key, content=photo_bytes)

    jobs: list[ImageJob] = []
    for variation_index in range(settings.MAX_RESTYLE_VARIATIONS):
        prompt = build_restyle_prompt(extra_styling, variation_index=variation_index)
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
        jobs.append(job)

    db.commit()
    for job in jobs:
        db.refresh(job)
        image_queue.enqueue(process_image_job, job.id, job_timeout=RESTYLE_JOB_TIMEOUT_SECONDS)

    return jobs


def select_restyle(db: Session, job_id: int) -> ImageJob:
    """
    Merchant picked their favorite variation from a restyle batch. Unlike
    select_draft, this does not enqueue a new render — restyle output is
    already full quality — it just records the preference and clears any
    prior selection in the same batch.
    """
    chosen = db.get(ImageJob, job_id)
    if chosen is None or chosen.stage != JobStage.RESTYLE:
        raise RestyleJobNotFound(f"No restyle job with id {job_id}")

    db.query(ImageJob).filter(
        ImageJob.batch_id == chosen.batch_id,
        ImageJob.stage == JobStage.RESTYLE,
        ImageJob.is_selected.is_(True),
    ).update({"is_selected": False})

    chosen.is_selected = True
    db.commit()
    db.refresh(chosen)
    return chosen


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