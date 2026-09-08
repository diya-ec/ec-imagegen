"""
Local smoke test — NOT part of the app. Verifies the whole draft -> select ->
final -> regenerate -> regen-cap flow works end to end using a stub inference
provider (no real DeepInfra calls, no API cost). Run with a local Redis up:

    python scripts/smoke_test.py
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke.db")
os.environ.setdefault("DEEPINFRA_API_KEY", "test-key")
os.environ.setdefault("MAX_FINAL_REGENS", "1")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass  # noqa: E402

import app.worker as worker_module  # noqa: E402
from app.db.database import SessionLocal, init_db  # noqa: E402
from app.db.models import ImageJob, JobStatus  # noqa: E402
from app.inference.base import GeneratedImage  # noqa: E402
from app.queue import image_queue, redis_conn  # noqa: E402
from app.schemas import CreateDraftBatchRequest, WizardAnswers  # noqa: E402
from app.services import job_service  # noqa: E402
from rq import SimpleWorker  # noqa: E402


class StubProvider:
    """Returns a tiny fake PNG instead of calling DeepInfra — for local testing only."""
    async def generate(self, *, prompt: str, model: str, size: str) -> GeneratedImage:
        fake_png = b"\x89PNG\r\n\x1a\n" + b"FAKE" * 10
        return GeneratedImage(content=fake_png, content_type="image/png",
                               provider="stub", model=model, cost_usd=0.01)


def get_stub_provider(_settings):
    return StubProvider()


def run_worker_burst():
    SimpleWorker([image_queue], connection=redis_conn).work(burst=True)


def main():
    worker_module.get_provider = get_stub_provider  # monkeypatch: no real API calls

    init_db()
    db = SessionLocal()

    print("1) Creating draft batch...")
    req = CreateDraftBatchRequest(
        restaurant_id="rest_1",
        menu_item_id="item_42",
        wizard_answers=WizardAnswers(dish_name="Paneer Tikka", cuisine_style="North Indian"),
    )
    drafts = job_service.create_draft_batch(db, req)
    batch_id = drafts[0].batch_id
    print(f"   -> {len(drafts)} draft jobs created, batch_id={batch_id}")

    run_worker_burst()

    db.expire_all()
    drafts = db.query(ImageJob).filter(ImageJob.batch_id == batch_id).all()
    for d in drafts:
        assert d.status == JobStatus.COMPLETED, f"draft {d.id} did not complete: {d.status} {d.error_message}"
    print(f"   -> all {len(drafts)} drafts COMPLETED, e.g. image_path={drafts[0].image_path}")

    print("2) Selecting a draft -> final render...")
    final_job = job_service.select_draft(db, drafts[0].id)
    run_worker_burst()
    db.expire_all()
    final_job = db.get(ImageJob, final_job.id)
    assert final_job.status == JobStatus.COMPLETED
    print(f"   -> final job {final_job.id} COMPLETED, model={final_job.model_used}, "
          f"cost=${final_job.cost_usd}, regen_count={final_job.regen_count}")

    print("3) Regenerating final (should succeed, within MAX_FINAL_REGENS=1)...")
    regen_job = job_service.regenerate_final(db, batch_id)
    run_worker_burst()
    db.expire_all()
    regen_job = db.get(ImageJob, regen_job.id)
    assert regen_job.status == JobStatus.COMPLETED
    assert regen_job.regen_count == 1
    print(f"   -> regen job {regen_job.id} COMPLETED, regen_count={regen_job.regen_count}")

    print("4) Regenerating again (should be REJECTED - regen cap reached)...")
    try:
        job_service.regenerate_final(db, batch_id)
        print("   -> FAIL: expected RegenLimitExceeded, none raised")
        sys.exit(1)
    except job_service.RegenLimitExceeded as e:
        print(f"   -> correctly rejected: {e}")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
