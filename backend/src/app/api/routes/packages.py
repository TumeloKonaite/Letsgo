from fastapi import APIRouter, Request

from app.domain.packages.service import PackageService
from app.schemas.package import PackageListResponse

router = APIRouter(prefix="/packages", tags=["packages"])


def get_package_service(request: Request) -> PackageService:
    return request.app.state.package_service


@router.get("", response_model=PackageListResponse)
def list_packages(request: Request) -> PackageListResponse:
    service = get_package_service(request)
    return service.list_packages()
