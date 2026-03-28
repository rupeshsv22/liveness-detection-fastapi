from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import liveness as liveness_router
from app.routes import ws as ws_router
from app.services.session import session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_manager.start_cleanup()
    yield
    session_manager.stop_cleanup()


app = FastAPI(
    title="Face Liveness Detection API",
    description="eKYC face liveness detection via webcam WebSocket stream.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(liveness_router.router)
app.include_router(ws_router.router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
