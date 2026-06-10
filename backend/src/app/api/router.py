from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.contact import router as contact_router
from app.api.routes.admin.auth import router as admin_auth_router
from app.api.routes.admin.bookings import router as admin_bookings_router
from app.api.routes.admin.package_images import router as admin_package_images_router
from app.api.routes.admin.packages import router as admin_packages_router
from app.api.routes.packages import router as packages_router
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.api_prefix)
api_router.include_router(packages_router)
api_router.include_router(chat_router)
api_router.include_router(contact_router)
api_router.include_router(admin_auth_router)
api_router.include_router(admin_bookings_router)
api_router.include_router(admin_packages_router)
api_router.include_router(admin_package_images_router)
