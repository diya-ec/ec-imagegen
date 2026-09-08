from fastapi import FastAPI

from app.db.database import init_db
from app.routers import jobs

app = FastAPI(title="ec-imagegen", version="0.1.0")

app.include_router(jobs.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
