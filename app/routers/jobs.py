from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import ImageJob
from app.schemas import JobOut, RestyleBatchOut, SelectRestyleRequest
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

settings = get_settings()


@router.post("/restyle", response_model=RestyleBatchOut, status_code=201)
async def create_restyle_batch(
    photo: UploadFile = File(...),                      # required
    restaurant_id: str | None = Form(None),              # optional
    menu_item_id: str | None = Form(None),                # optional
    extra_styling: str | None = Form(None),               # optional
    db: Session = Depends(get_db),
):
    if photo.content_type not in settings.ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{photo.content_type}'. "
                   f"Allowed: {', '.join(sorted(settings.ALLOWED_UPLOAD_CONTENT_TYPES))}",
        )

    # Read up to the limit + 1 byte so we can detect "too big" without
    # loading an arbitrarily huge file into memory first.
    photo_bytes = await photo.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    if len(photo_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
        )
    if len(photo_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    jobs = job_service.create_restyle_batch(
        db,
        restaurant_id=restaurant_id,
        menu_item_id=menu_item_id,
        extra_styling=extra_styling,
        photo_bytes=photo_bytes,
        photo_filename=photo.filename or "upload.jpg",
    )
    return RestyleBatchOut(batch_id=jobs[0].batch_id, jobs=jobs)


@router.post("/restyle/select", response_model=JobOut, status_code=201)
def select_restyle(req: SelectRestyleRequest, db: Session = Depends(get_db)):
    try:
        return job_service.select_restyle(db, req.job_id)
    except job_service.RestyleJobNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ImageJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/batch/{batch_id}", response_model=list[JobOut])
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    jobs = db.query(ImageJob).filter(ImageJob.batch_id == batch_id).order_by(ImageJob.created_at).all()
    if not jobs:
        raise HTTPException(status_code=404, detail="Batch not found")
    return jobs