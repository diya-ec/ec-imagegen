from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import init_db
from app.routers import jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    # (no shutdown work needed today; add cleanup here if that changes)


app = FastAPI(title="ec-imagegen", version="0.2.0", lifespan=lifespan)

app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}