from app.domain.packages.repository import PackageRecord, PackageRepository
from app.schemas.package import PackageListResponse, PackageResponse


class PackageService:
    def __init__(self, repository: PackageRepository) -> None:
        self._repository = repository

    def list_packages(self) -> PackageListResponse:
        packages = [self._to_response(package) for package in self._repository.list_packages()]
        return PackageListResponse(items=packages, total=len(packages))

    def _to_response(self, package: PackageRecord) -> PackageResponse:
        if package.price_zar < 0:
            raise ValueError("Package price cannot be negative.")
        if package.duration_days <= 0:
            raise ValueError("Package duration must be greater than zero.")

        return PackageResponse(
            id=package.id,
            name=package.name,
            location=package.location,
            description=package.description,
            price_zar=package.price_zar,
            duration_days=package.duration_days,
            is_active=package.is_active,
        )
