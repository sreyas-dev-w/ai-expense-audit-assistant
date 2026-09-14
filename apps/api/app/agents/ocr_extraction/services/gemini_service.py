import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.agents.ocr_extraction.prompts import (
    RECEIPT_EXTRACTION_PROMPT,
)
from app.agents.ocr_extraction.schemas import Extraction


load_dotenv()


class GeminiService:

    def __init__(self):
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
    ) -> Extraction:

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_text(
                    text=RECEIPT_EXTRACTION_PROMPT
                ),
                types.Part.from_bytes(
                    data=receipt_bytes,
                    mime_type=mime_type,
                ),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Extraction,
                temperature=0,
            ),
        )

        if response.parsed is not None:
            return response.parsed

        return Extraction.model_validate_json(
            response.text
        )