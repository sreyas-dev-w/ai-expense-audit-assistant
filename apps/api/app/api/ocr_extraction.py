from datetime import date
from typing import Literal

from fastapi import APIRouter, File, Form, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.ocr_agent import OCRAgent
from app.schemas.extraction import OCRResponse
from app.db.session import get_db_session


router = APIRouter(
    prefix="/api/v1/ocr",
    tags=["OCR Extraction"],
)


@router.post("/extract", response_model=OCRResponse)
async def extract_receipt(
    # ==================================================
    # COMMON FIELDS
    # ==================================================

    employee_id: str = Form(...),

    expense_category: Literal[
        "FOOD_MEALS",
        "TRAVEL",
        "ACCOMMODATION",
        "OTHERS",
    ] = Form(...),

    receipt: UploadFile = File(...),

    # ==================================================
    # COMMON / CATEGORY-SPECIFIC
    # ==================================================

    spend_amount: float | None = Form(None),

    business_purpose: str | None = Form(None),

    # ==================================================
    # FOOD_MEALS
    # ==================================================

    meal_type: Literal[
        "VEG",
        "NON_VEG",
        "MIXED",
    ] | None = Form(None),

    number_of_people: int | None = Form(None),

    # ==================================================
    # TRAVEL
    # ==================================================

    travel_type: Literal[
        "FLIGHT",
        "TRAIN",
        "BUS",
        "CAR",
        "BIKE",
    ] | None = Form(None),

    origin: str | None = Form(None),

    destination: str | None = Form(None),

    travel_class: Literal[
        "BUSINESS_CLASS",
        "ECONOMY_CLASS",
    ] | None = Form(None),

    # ==================================================
    # ACCOMMODATION
    # ==================================================

    location: str | None = Form(None),

    check_in_date: date | None = Form(None),

    check_out_date: date | None = Form(None),

    number_of_days: int | None = Form(None),

    room_type: str | None = Form(None),

    # ==================================================
    # OTHERS
    # ==================================================

    expense_type: str | None = Form(None),

    additional_details: str | None = Form(None),

    session: AsyncSession = Depends(get_db_session),
):

    # ==================================================
    # READ RECEIPT
    # ==================================================

    receipt_bytes = await receipt.read()

    # ==================================================
    # INITIALIZE OCR AGENT
    # ==================================================

    ocr_agent = OCRAgent(session=session)

    # ==================================================
    # SEND TO OCR AGENT
    # ==================================================

    result = await ocr_agent.process(
        employee_id=employee_id,
        expense_category=expense_category,

        spend_amount=spend_amount,
        business_purpose=business_purpose,

        # FOOD_MEALS
        meal_type=meal_type,
        number_of_people=number_of_people,

        # TRAVEL
        travel_type=travel_type,
        origin=origin,
        destination=destination,
        travel_class=travel_class,

        # ACCOMMODATION
        location=location,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        number_of_days=number_of_days,
        room_type=room_type,

        # OTHERS
        expense_type=expense_type,
        additional_details=additional_details,

        # RECEIPT
        receipt_bytes=receipt_bytes,
        mime_type=receipt.content_type,
    )

    return result