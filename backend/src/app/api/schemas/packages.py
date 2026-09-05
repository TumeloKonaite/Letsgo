"""Define public package views and admin payloads, including nested ordering rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.infrastructure.database.models import PackagePublicationStatus


class PackageImage(BaseModel):
    id: int
    image_url: str
    alt_text: str | None = None
    sort_order: int = Field(..., ge=0)
    is_cover: bool = False


class ItineraryItem(BaseModel):
    id: int
    title: str
    description: str
    duration: str | None = Field(default=None, max_length=100)
    display_order: int = Field(..., ge=0)


class PackageInclusion(BaseModel):
    id: int
    name: str
    type: str
    display_order: int = Field(..., ge=0)


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
    inclusions: list[PackageInclusion]
    availability: list[AvailabilityItem]


class AdminPackageItineraryInput(BaseModel):
    id: int | None = None
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    duration: str | None = Field(default=None, max_length=100)
    display_order: int = Field(default=0, ge=0)


class AdminPackageInclusionInput(BaseModel):
    id: int | None = None
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., pattern="^(included|excluded)$")
    display_order: int = Field(default=0, ge=0)


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
    itinerary: list[AdminPackageItineraryInput] = Field(default_factory=list)
    inclusions: list[AdminPackageInclusionInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_nested_display_orders(self) -> AdminPackageBase:
        _validate_nested_display_orders(self.itinerary, self.inclusions)
        return self


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
    itinerary: list[AdminPackageItineraryInput] | None = None
    inclusions: list[AdminPackageInclusionInput] | None = None

    @model_validator(mode="after")
    def validate_nested_display_orders(self) -> PackageUpdate:
        _validate_nested_display_orders(self.itinerary, self.inclusions)
        return self


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


class AdminPackageImageResponse(BaseModel):
    id: int
    package_id: int
    url: str
    alt_text: str | None = None
    display_order: int
    is_cover: bool


class AdminPackageResponse(PackageResponse):
    itinerary: list[ItineraryItem] = Field(default_factory=list)
    inclusions: list[PackageInclusion] = Field(default_factory=list)


def _validate_nested_display_orders(
    itinerary: list[AdminPackageItineraryInput] | None,
    inclusions: list[AdminPackageInclusionInput] | None,
) -> None:
    if itinerary is not None:
        itinerary_orders = [item.display_order for item in itinerary]
        if len(itinerary_orders) != len(set(itinerary_orders)):
            raise ValueError("Itinerary display_order values must be unique.")

    if inclusions is not None:
        for inclusion_type in ("included", "excluded"):
            scoped_orders = [
                item.display_order for item in inclusions if item.type == inclusion_type
            ]
            if len(scoped_orders) != len(set(scoped_orders)):
                raise ValueError(
                    f"{inclusion_type.title()} item display_order values must be unique."
                )
