from fastapi import APIRouter, File, Form, UploadFile

from app.agents.ocr_extraction.agent import OCRAgent
from app.agents.ocr_extraction.schemas import OCRResponse


router = APIRouter(
    prefix="/api/v1/ocr",
    tags=["OCR Extraction"],
)

ocr_agent = OCRAgent()


@router.post("/extract", response_model=OCRResponse)
async def extract_receipt(
    employee_id: str = Form(...),
    declared_category: str = Form(...),
    spend_amount: float = Form(...),
    business_purpose: str = Form(...),
    receipt: UploadFile = File(...),
):
    receipt_bytes = await receipt.read()

    result = await ocr_agent.process(
    employee_id=employee_id,
    declared_category=declared_category,
    spend_amount=spend_amount,
    business_purpose=business_purpose,
    receipt_bytes=receipt_bytes,
    mime_type=receipt.content_type,
)

    return result