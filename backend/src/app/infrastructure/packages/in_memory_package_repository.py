from decimal import Decimal

from app.domain.packages.repository import PackageRecord


class InMemoryPackageRepository:
    def __init__(self) -> None:
        self._packages = [
            PackageRecord(
                id=1,
                name="Cape Town Explorer",
                location="Cape Town",
                description="A placeholder coastal package for initial API development.",
                price_zar=Decimal("2499.00"),
                duration_days=3,
            ),
            PackageRecord(
                id=2,
                name="Kruger Weekend Safari",
                location="Mpumalanga",
                description="A placeholder wildlife package for local development.",
                price_zar=Decimal("5299.00"),
                duration_days=2,
            ),
        ]

    def list_packages(self) -> list[PackageRecord]:
        return list(self._packages)
