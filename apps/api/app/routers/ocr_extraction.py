from typing import Literal

from fastapi import APIRouter, File, Form, UploadFile

from app.agents.ocr_agent import OCRAgent
from app.schemas.extraction import Extraction


router = APIRouter(
    prefix="/api/v1/ocr",
    tags=["OCR Extraction"],
)

ocr_agent = OCRAgent()


@router.post("/extract", response_model=Extraction)
async def extract_receipt(
    expense_category: Literal[
        "FOOD_MEALS",
        "TRAVEL",
        "ACCOMMODATION",
        "OTHERS",
    ] = Form(...),
    receipt: UploadFile = File(...),
):
    """Extract receipt data based on expense category."""

    receipt_bytes = await receipt.read()

    result = await ocr_agent.process(
        expense_category=expense_category,
        receipt_bytes=receipt_bytes,
        mime_type=receipt.content_type,
    )

    return result