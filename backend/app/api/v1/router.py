from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.banking import router as banking_router
from app.api.v1.endpoints.pigs import router as pigs_router
from app.api.v1.endpoints.family import router as family_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(banking_router)
api_router.include_router(pigs_router)
api_router.include_router(family_router)
