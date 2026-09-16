"""Text extraction from policy PDFs using pypdf."""
from pathlib import Path

from pypdf import PdfReader


class PdfExtractionError(Exception):
    def __init__(self, message: str, *, code: str = "pdf_extraction_error"):
        super().__init__(message)
        self.code = code


def extract_pdf_text(path: str | Path) -> list[str]:
    """Return the extracted text of each PDF page, in page order.

    Raises ``PdfExtractionError`` when the file cannot be parsed or a page
    contains no extractable text (a scanned document, for instance).
    """
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise PdfExtractionError(
            f"Failed to open PDF at {path}: {exc}"
        ) from exc

    pages: list[str] = []
    try:
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                raise PdfExtractionError(
                    f"Page {index} of {path} contains no extractable text; "
                    "scanned PDFs require an OCR stage"
                )
            pages.append(text)
    except PdfExtractionError:
        raise
    except Exception as exc:
        raise PdfExtractionError(
            f"Failed to extract text from {path}: {exc}"
        ) from exc
    return pages