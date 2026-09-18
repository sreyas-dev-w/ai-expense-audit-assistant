import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.schemas.extraction import (
    FoodMealsExtraction,
    TravelExtraction,
    AccommodationExtraction,
    OtherExtraction,
    Extraction,
)

_PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "ocr_extraction_prompt.txt"

load_dotenv()


class GeminiService:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3.5-flash-lite"

    def _load_prompt(self) -> str:
        """Load OCR extraction prompt from text file"""
        return _PROMPT_FILE.read_text()

    async def extract_receipt(
        self,
        receipt_bytes: bytes,
        mime_type: str,
        expense_category: str,
    ) -> Extraction:
        """Extract receipt data from image using Gemini vision."""

        expense_category = expense_category.strip().upper()

        # Select schema based on category
        schema_map = {
            "FOOD_MEALS": FoodMealsExtraction,
            "TRAVEL": TravelExtraction,
            "ACCOMMODATION": AccommodationExtraction,
            "OTHERS": OtherExtraction,
        }

        if expense_category not in schema_map:
            raise ValueError(f"Unsupported expense category: {expense_category}")

        extraction_schema = schema_map[expense_category]

        print(f"[GEMINI] Extracting {expense_category} receipt data.")

        prompt = self._load_prompt().replace(
    "{expense_category}",
    expense_category,
)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=receipt_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=extraction_schema,
                temperature=0,
            ),
        )

        # Use structured parsing if available, fallback to JSON parsing
        if response.parsed is not None:
            print("[GEMINI] Extraction successful.")
            return response.parsed

        print("[GEMINI] Fallback JSON parsing.")
        return extraction_schema.model_validate_json(response.text)