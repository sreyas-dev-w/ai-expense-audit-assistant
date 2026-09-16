"""Expense category data contracts.

Each expense category has its own well-defined ``category_data`` payload. The
structure is fixed per category: the claim schema (``app/schemas/claim.py``)
discriminates on ``category`` and validates ``category_data`` against exactly
one of these models.
"""
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_header: str
    item_amount: Decimal


class FoodMealsData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_type: str
    merchant_name: str
    number_of_people: int = Field(ge=1)
    line_items: list[LineItem]


class TravelData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    travel_type: str
    origin: str
    destination: str
    travel_date: date
    travel_class: str | None = None
    ticket_number: str | None = None
    line_items: list[LineItem]


class AccommodationData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hotel_name: str
    location: str
    check_in: date
    check_out: date
    number_of_nights: int = Field(ge=1)
    no_of_rooms: int = Field(ge=1)
    room_type: str | None = None
    line_items: list[LineItem]


class OtherData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expense_type: str
    merchant_name: str | None = None
    additional_details: dict[str, Any] | None = None
    line_items: list[LineItem]