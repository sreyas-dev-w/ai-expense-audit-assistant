"""Receipt retrieval tool.

Resolves a claim's ``receipt_url`` into the bytes + MIME type the OCR agent
needs. Supports http(s) URLs and local filesystem paths (the current no-S3
storage backing). Kept intentionally narrow: it returns bytes, never paths into
application data.
"""
import asyncio
import mimetypes
from pathlib import Path

import httpx

from app.schemas.audit import ReceiptData
from app.tools.base import AuditTool, AuditToolError

_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_DEFAULT_TIMEOUT_SECONDS = 30


class FetchReceiptTool(AuditTool):
    """Fetch a claim receipt and normalize it for the OCR agent."""

    name = "fetch_receipt"
    description = "Fetch a claim receipt (http(s) URL or local path) as bytes + MIME type."

    def __init__(self, *, timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS):
        self._timeout_seconds = timeout_seconds

    async def run(self, *, receipt_url: str) -> ReceiptData:
        if not receipt_url or not receipt_url.strip():
            raise AuditToolError(
                "receipt_url is required", code="missing_receipt_url"
            )

        source = receipt_url.strip()
        try:
            if source.startswith(("http://", "https://")):
                content, mime_type = await asyncio.wait_for(
                    self._fetch_url(source), timeout=self._timeout_seconds
                )
            else:
                content, mime_type = self._read_local(source)
        except asyncio.TimeoutError as exc:
            raise AuditToolError(
                "Timed out while fetching the receipt",
                code="receipt_fetch_timeout",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise AuditToolError(
                f"Receipt fetch failed: {exc}",
                code="receipt_fetch_failed",
                retryable=True,
            ) from exc
        except OSError as exc:
            raise AuditToolError(
                f"Receipt file read failed: {exc}",
                code="receipt_read_failed",
            ) from exc

        mime = mime_type or mimetypes.guess_type(source)[0] or ""
        normalized = mime.split(";")[0].strip().lower()
        if normalized not in _ALLOWED_MIME_TYPES:
            raise AuditToolError(
                f"Unsupported receipt format: {mime or 'unknown'}",
                code="unsupported_receipt_format",
            )
        if not content:
            raise AuditToolError(
                "Receipt was fetched but contained no content",
                code="empty_receipt",
            )
        return ReceiptData(content=content, mime_type=normalized, source=source)

    async def _fetch_url(self, url: str) -> tuple[bytes, str | None]:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=self._timeout_seconds
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
        return response.content, response.headers.get("content-type")

    @staticmethod
    def _read_local(path: str) -> tuple[bytes, str | None]:
        local = Path(path)
        if not local.is_file():
            raise FileNotFoundError(f"Receipt not found at {path}")
        return local.read_bytes(), mimetypes.guess_type(local.name)[0]