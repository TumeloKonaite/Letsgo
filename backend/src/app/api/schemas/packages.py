from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


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

