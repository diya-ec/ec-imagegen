from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ImageJob
from app.schemas import (
    CreateDraftBatchRequest,
    DraftBatchOut,
    JobOut,
    RegenerateFinalRequest,
    SelectDraftRequest,
)
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/drafts", response_model=DraftBatchOut, status_code=201)
def create_draft_batch(req: CreateDraftBatchRequest, db: Session = Depends(get_db)):
    jobs = job_service.create_draft_batch(db, req)
    return DraftBatchOut(batch_id=jobs[0].batch_id, jobs=jobs)


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


@router.post("/select", response_model=JobOut, status_code=201)
def select_draft(req: SelectDraftRequest, db: Session = Depends(get_db)):
    try:
        return job_service.select_draft(db, req.draft_job_id)
    except job_service.DraftNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/regenerate", response_model=JobOut, status_code=201)
def regenerate_final(req: RegenerateFinalRequest, db: Session = Depends(get_db)):
    try:
        return job_service.regenerate_final(db, req.batch_id)
    except job_service.DraftNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except job_service.RegenLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
