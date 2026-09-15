import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.prompts.ocr_extraction_prompt import (
    RECEIPT_EXTRACTION_PROMPT,
)

from app.schemas.extraction import (
    FoodMealsExtraction,
    TravelExtraction,
    AccommodationExtraction,
    OtherExtraction,
)


load_dotenv()


class GeminiService:

    def __init__(self):
        # ==================================================
        # Gemini API configuration
        # ==================================================

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = "gemini-3.6-flash"

    async def extract_receipt(
        self,
        receipt_bytes: bytes,
        mime_type: str,
        expense_category: str,
    ):
        # ==================================================
        # 1. Normalize category
        # ==================================================

        expense_category = expense_category.strip().upper()

        # ==================================================
        # 2. Select extraction schema
        # ==================================================

        if expense_category == "FOOD_MEALS":

            extraction_schema = FoodMealsExtraction

        elif expense_category == "TRAVEL":

            extraction_schema = TravelExtraction

        elif expense_category == "ACCOMMODATION":

            extraction_schema = AccommodationExtraction

        elif expense_category == "OTHERS":

            extraction_schema = OtherExtraction

        else:

            raise ValueError(
                f"Unsupported expense category: "
                f"{expense_category}"
            )

        print(
            f"[GEMINI] Using extraction schema: "
            f"{extraction_schema.__name__}"
        )

        # ==================================================
        # 3. Build category-aware prompt
        # ==================================================

        prompt = RECEIPT_EXTRACTION_PROMPT.format(
            expense_category=expense_category
        )

        # ==================================================
        # 4. Send receipt to Gemini
        # ==================================================

        print(
            f"[GEMINI] Sending receipt for "
            f"category '{expense_category}'."
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,

            contents=[
                types.Part.from_text(
                    text=prompt
                ),

                types.Part.from_bytes(
                    data=receipt_bytes,
                    mime_type=mime_type,
                ),
            ],

            config=types.GenerateContentConfig(
                response_mime_type="application/json",

                response_schema=extraction_schema,

                temperature=0,
            ),
        )

        # ==================================================
        # 5. Parse structured Gemini response
        # ==================================================

        if response.parsed is not None:

            print(
                "[GEMINI] Structured response parsed successfully."
            )

            return response.parsed

        # ==================================================
        # 6. Fallback JSON parsing
        # ==================================================

        print(
            "[GEMINI WARNING] "
            "Structured response was not available. "
            "Parsing response text manually."
        )

        return extraction_schema.model_validate_json(
            response.text
        )