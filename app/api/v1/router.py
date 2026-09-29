from fastapi import APIRouter

from app.api.v1.routes import chat, ingestion

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(ingestion.router)
api_router.include_router(chat.router)