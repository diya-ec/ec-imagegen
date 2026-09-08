# ec-imagegen

Backend for AI-generated/enhanced merchant menu photos. Currently wired to
**DeepInfra's hosted API** (FLUX-2-max) instead of self-hosting a model —
this is a deliberate placeholder while the team researches and fine-tunes an
open-weight model to self-host later. The swap point is `app/inference/`:
add a new `InferenceProvider` implementation there and flip
`INFERENCE_PROVIDER` in config; nothing else changes.

## Strategy implemented here

1. Merchant answers guided wizard questions (no free-text prompting) →
   `app/services/prompt_builder.py` turns that into a prompt.
2. **Draft stage**: `MAX_DRAFT_VARIATIONS` (default 3) cheap previews are
   generated on `DRAFT_MODEL` (FLUX-2-klein).
3. Merchant picks one draft → **final stage**: one render on `FINAL_MODEL`
   (FLUX-2-max), same prompt.
4. If the flagship render still isn't right, one safety-valve regen is
   allowed (`MAX_FINAL_REGENS`, default 1) — same prompt, fresh generation —
   before the API returns `429`.

This is scoped to **text-to-image only** for now (no reference-photo
enhance/image-to-image path yet).

## Architecture

```
FastAPI (app/main.py, app/routers/jobs.py)
   -> writes ImageJob rows (app/db/models.py)
   -> enqueues app.worker.process_image_job onto Redis/RQ (app/queue.py)

RQ worker (separate process, app/worker.py)
   -> calls InferenceProvider.generate() (app/inference/deepinfra.py)
   -> saves image via StorageBackend (app/services/storage.py, local disk for now)
   -> updates the ImageJob row (status, image_path, cost, model_used)
```

Async job queue was kept intentionally — DeepInfra calls are I/O-bound
(a few seconds per image), so a queue absorbs bursts (e.g. 150 images for
one restaurant) and lets a single worker handle many requests concurrently,
without the GPU-serving complexity the earlier self-hosted plan needed.

## Local setup (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DEEPINFRA_API_KEY, and either point DATABASE_URL at a
# local Postgres or swap it for sqlite:///./dev.db for quick testing

# Redis must be running locally (redis-server), Postgres too if you kept
# the Postgres DATABASE_URL.

# Terminal 1 — API
uvicorn app.main:app --reload

# Terminal 2 — worker
python scripts/run_worker.py
```

Then:
```bash
curl -X POST localhost:8000/jobs/drafts -H "Content-Type: application/json" -d '{
  "restaurant_id": "rest_1",
  "menu_item_id": "item_42",
  "wizard_answers": {"dish_name": "Paneer Tikka", "cuisine_style": "North Indian"}
}'
# -> poll GET /jobs/{id} or GET /jobs/batch/{batch_id} until status=completed

curl -X POST localhost:8000/jobs/select -H "Content-Type: application/json" \
  -d '{"draft_job_id": 1}'

curl -X POST localhost:8000/jobs/regenerate -H "Content-Type: application/json" \
  -d '{"batch_id": "<batch_id>"}'
```

## Local setup (Docker Compose)

```bash
cp .env.example .env   # set DEEPINFRA_API_KEY at minimum
docker compose up --build
```

## Smoke test (no real API calls, no cost)

Verifies the full draft -> select -> final -> regenerate -> regen-cap flow
using a stub inference provider:

```bash
python scripts/smoke_test.py
```

## Not yet built (flagged, not silently skipped)

- Image-to-image / reference-photo enhance path (deferred per current scope)
- S3 storage backend (`StorageBackend` interface is ready; `S3Storage` is a stub)
- DINOv2 similarity QA gate, merchant quotas, tiered billing, autoscaling —
  these were scoped in earlier planning and still apply once this core loop
  is validated; not wired into this cut
- Alembic migrations (using `Base.metadata.create_all` for local dev)
