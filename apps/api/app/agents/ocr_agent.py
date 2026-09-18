import logging
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from app.core.logging import to_loggable
from app.schemas.extraction import (
    FoodMealsExtraction,
    TravelExtraction,
    AccommodationExtraction,
    OtherExtraction,
    Extraction,
)
from app.services.ocr_extraction_gemini_service import GeminiService

logger = logging.getLogger(__name__)


class OCRState(TypedDict, total=False):
    """State for OCR extraction workflow"""

    expense_category: str
    receipt_bytes: Optional[bytes]
    mime_type: Optional[str]
    extraction: Optional[Extraction]


class OCRAgent:
    """Simple OCR extraction agent that extracts receipt data per category."""

    def __init__(self):
        self.gemini_service = GeminiService()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build minimal LangGraph workflow"""
        workflow = StateGraph(OCRState)

        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("extract_receipt", self._extract_receipt)

        workflow.add_edge(START, "validate_input")
        workflow.add_edge("validate_input", "extract_receipt")
        workflow.add_edge("extract_receipt", END)

        return workflow.compile()

    async def process(
        self,
        expense_category: str,
        receipt_bytes: bytes,
        mime_type: str,
    ) -> Extraction:
        """Extract receipt data based on expense category."""

        initial_state: OCRState = {
            "expense_category": expense_category,
            "receipt_bytes": receipt_bytes,
            "mime_type": mime_type,
        }

        result = await self.graph.ainvoke(initial_state)
        return result["extraction"]

    async def _validate_input(self, state: OCRState) -> OCRState:
        """Validate input parameters"""

        expense_category = state.get("expense_category")
        if not expense_category:
            raise ValueError("Expense category is required.")

        expense_category = expense_category.strip().upper()

        allowed_categories = {"FOOD_MEALS", "TRAVEL", "ACCOMMODATION", "OTHERS"}
        if expense_category not in allowed_categories:
            raise ValueError(
                f"Invalid expense category: {expense_category}. "
                "Allowed categories are FOOD_MEALS, TRAVEL, ACCOMMODATION, OTHERS."
            )

        state["expense_category"] = expense_category

        receipt_bytes = state.get("receipt_bytes")
        if not receipt_bytes:
            raise ValueError("Receipt file is required.")

        mime_type = state.get("mime_type")
        allowed_mime_types = {"image/jpeg", "image/png", "application/pdf"}

        if mime_type not in allowed_mime_types:
            raise ValueError(
                f"Unsupported receipt format: {mime_type}. "
                "Supported formats are PNG, JPEG, and PDF."
            )

        logger.info(
            "OCR agent input: expense_category=%s mime_type=%s receipt_bytes=%d",
            expense_category,
            mime_type,
            len(receipt_bytes),
        )
        return state

    async def _extract_receipt(self, state: OCRState) -> OCRState:
        """Extract receipt using Gemini"""

        expense_category = state["expense_category"]
        receipt_bytes = state["receipt_bytes"]
        mime_type = state["mime_type"]

        logger.info("OCR agent extracting %s receipt with Gemini.", expense_category)

        extraction = await self.gemini_service.extract_receipt(
            receipt_bytes=receipt_bytes,
            mime_type=mime_type,
            expense_category=expense_category,
        )

        logger.info("OCR agent output: %s", to_loggable(extraction))
        state["extraction"] = extraction
        return state