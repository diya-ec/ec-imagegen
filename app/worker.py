import asyncio
import logging

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import ImageJob, JobStage, JobStatus
from app.inference.base import InferenceError
from app.inference.deepinfra import get_provider
from app.inference.replicate_provider import get_restyle_provider
from app.services.storage import get_storage

logger = logging.getLogger(__name__)
settings = get_settings()


def process_image_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(ImageJob, job_id)
        if job is None:
            logger.error("process_image_job: no job with id %s", job_id)
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        storage = get_storage(settings)

        try:
            if job.stage == JobStage.RESTYLE:
                provider = get_restyle_provider(settings)
                model = settings.RESTYLE_MODEL
                source_bytes = storage.read(job.source_image_path)
                result = asyncio.run(
                    provider.generate(
                        prompt=job.prompt,
                        model=model,
                        size=settings.IMAGE_SIZE,
                        input_image=source_bytes,
                    )
                )
            else:
                model = settings.DRAFT_MODEL if job.stage == JobStage.DRAFT else settings.FINAL_MODEL
                provider = get_provider(settings)
                result = asyncio.run(
                    provider.generate(prompt=job.prompt, model=model, size=settings.IMAGE_SIZE)
                )
        except InferenceError as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            db.commit()
            logger.error("Image generation failed for job %s: %s", job_id, e)
            return

        key = f"{job.restaurant_id}/{job.menu_item_id}/{job.batch_id}/{job.stage.value}_{job.id}.png"
        path = storage.save(key=key, content=result.content)

        job.status = JobStatus.COMPLETED
        job.image_path = path
        job.model_used = result.model
        job.cost_usd = result.cost_usd
        db.commit()

    finally:
        db.close()