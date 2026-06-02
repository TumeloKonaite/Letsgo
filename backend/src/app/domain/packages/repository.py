from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PackageRecord:
    id: int
    name: str
    location: str
    description: str | None
    price_zar: Decimal
    duration_days: int
    is_active: bool = True


class PackageRepository(Protocol):
    def list_packages(self) -> list[PackageRecord]:
        """Return all available packages."""
