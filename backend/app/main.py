from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import data
from app.api.v1 import router as v1_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="Milky Way Explorer API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    application.include_router(v1_router)
    application.include_router(data.router)
    return application


app = create_app()
