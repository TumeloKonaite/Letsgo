from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field
from app.infrastructure.database.models import PackagePublicationStatus


class PackageImage(BaseModel):
    id: int
    image_url: str
    alt_text: str | None = None
    sort_order: int = Field(..., ge=0)
    is_cover: bool = False


class ItineraryItem(BaseModel):
    id: int
    day_number: int = Field(..., gt=0)
    title: str
    description: str
    sort_order: int = Field(..., ge=0)


class AvailabilityItem(BaseModel):
    id: int
    start_date: date
    end_date: date
    capacity: int = Field(..., gt=0)
    spots_available: int = Field(..., ge=0)
    status: str


class PackageListItem(BaseModel):
    id: int
    slug: str
    title: str
    short_description: str | None = None
    location: str
    duration_days: int = Field(..., gt=0)
    price_from: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    hero_image_url: str | None = None
    is_featured: bool = False


class PackageDetail(BaseModel):
    id: int
    slug: str
    title: str
    short_description: str | None = None
    full_description: str
    location: str
    duration_days: int = Field(..., gt=0)
    price_from: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    hero_image_url: str | None = None
    is_featured: bool = False
    images: list[PackageImage]
    itinerary: list[ItineraryItem]
    availability: list[AvailabilityItem]


class AdminPackageBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=500)
    description: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1, max_length=150)
    duration_days: int = Field(..., gt=0)
    duration_nights: int = Field(..., ge=0)
    price_from: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    is_active: bool = True
    status: PackagePublicationStatus = PackagePublicationStatus.DRAFT
    is_published: bool = False
    is_featured: bool = False
    display_order: int = Field(default=0, ge=0)


class PackageCreate(AdminPackageBase):
    pass


class PackageUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, min_length=1)
    destination: str | None = Field(default=None, min_length=1, max_length=150)
    duration_days: int | None = Field(default=None, gt=0)
    duration_nights: int | None = Field(default=None, ge=0)
    price_from: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
    status: PackagePublicationStatus | None = None
    is_published: bool | None = None
    is_featured: bool | None = None
    display_order: int | None = Field(default=None, ge=0)


class PackageResponse(BaseModel):
    id: int
    title: str
    slug: str
    short_description: str | None = None
    description: str
    destination: str
    duration_days: int
    duration_nights: int
    price_from: Decimal
    currency: str
    is_active: bool
    status: PackagePublicationStatus
    is_published: bool
    is_featured: bool
    display_order: int


class AdminPackageCreateRequest(PackageCreate):
    pass


class AdminPackagePutRequest(PackageCreate):
    pass


class AdminPackagePatchRequest(PackageUpdate):
    pass


class AdminPackageImageCreateRequest(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=2048)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int = Field(default=0, ge=0)
    is_cover: bool = False


class AdminPackageImageResponse(BaseModel):
    id: int
    image_url: str
    alt_text: str | None = None
    sort_order: int
    is_cover: bool


class AdminPackageResponse(PackageResponse):
    pass
