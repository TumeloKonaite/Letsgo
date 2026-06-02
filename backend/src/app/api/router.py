from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.packages import router as packages_router
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.api_prefix)
api_router.include_router(packages_router)
api_router.include_router(admin_router)
