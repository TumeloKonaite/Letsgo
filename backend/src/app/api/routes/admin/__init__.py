from fastapi import APIRouter

from app.api.routes.admin.auth import router as auth_router
from app.api.routes.admin.packages import router as packages_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(packages_router)

__all__ = ["router"]
