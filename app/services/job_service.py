import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ImageJob, JobStatus
from app.queue import image_queue
from app.services.prompt_builder import build_restyle_prompt
from app.services.storage import get_storage
from app.worker import process_image_job

settings = get_settings()


class RestyleJobNotFound(Exception):
    pass


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
    (Replicate) into MAX_RESTYLE_VARIATIONS distinct-looking options. The
    source photo is uploaded and saved exactly once; every variation job in
    the batch points at the same source_image_path and only differs in its
    prompt (via a rotated style directive from prompt_builder) and,
    downstream, its generation result.
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
            status=JobStatus.PENDING,
            prompt=prompt,
            source_image_path=source_path,
        )
        db.add(job)
        jobs.append(job)

    db.commit()
    for job in jobs:
        db.refresh(job)
        image_queue.enqueue(
            process_image_job, job.id, job_timeout=settings.RESTYLE_JOB_TIMEOUT_SECONDS
        )

    return jobs


def select_restyle(db: Session, job_id: int) -> ImageJob:
    """
    Merchant picked their favorite variation from a restyle batch. This does
    not enqueue a new render — restyle output is already full quality — it
    just records the preference and clears any prior selection in the same
    batch.
    """
    chosen = db.get(ImageJob, job_id)
    if chosen is None:
        raise RestyleJobNotFound(f"No restyle job with id {job_id}")

    db.query(ImageJob).filter(
        ImageJob.batch_id == chosen.batch_id,
        ImageJob.is_selected.is_(True),
    ).update({"is_selected": False})

    chosen.is_selected = True
    db.commit()
    db.refresh(chosen)
    return chosen