from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    description: str | None = None
    price_zar: Decimal = Field(..., ge=0)
    duration_days: int = Field(..., gt=0)
    is_active: bool = True


class PackageListResponse(BaseModel):
    items: list[PackageResponse]
    total: int = Field(..., ge=0)


class CreatePackageRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    location: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    price_zar: Decimal = Field(..., ge=0)
    duration_days: int = Field(..., gt=0)


class UpdatePackageRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    price_zar: Decimal | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
