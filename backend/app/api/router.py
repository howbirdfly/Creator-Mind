from fastapi import APIRouter

from app.api.routes import conversations, health, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(conversations.router)
api_router.include_router(sources.router)
