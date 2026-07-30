"""Aggregates every V1 router. New endpoints get registered here only."""

from fastapi import APIRouter

from app.api.v1 import meta, search

router = APIRouter(prefix="/api/v1")
router.include_router(meta.router)
router.include_router(search.router)
