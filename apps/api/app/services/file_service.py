"""Filesystem storage for uploaded policy documents and claim receipts.

Files land in backend-local dump directories ("storage_dump/policies" and
"storage_dump/receipts" under ``apps/api`` by default, configurable via
``POLICY_STORAGE_DIR`` / ``RECEIPT_STORAGE_DIR``). Stored file names are
prefixed with a random id so repeated uploads never collide while keeping the
original base name for traceability.
"""
import re
import uuid
from pathlib import Path

from app.core.config import settings

RECEIPT_SUFFIXES = {".png", ".jpg", ".jpeg", ".pdf"}
_STORED_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def _resolve(path: Path) -> Path:
    base = Path(__file__).resolve().parents[2]
    resolved = base / path if not path.is_absolute() else path
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def policy_storage_dir() -> Path:
    return _resolve(settings.policy_storage_dir)


def receipt_storage_dir() -> Path:
    return _resolve(settings.receipt_storage_dir)


def store_receipt(filename: str, content: bytes) -> Path:
    """Persist an uploaded receipt and return its path.

    The extension drives the MIME type the OCR agent sends to Gemini
    (``app/tools/audit_tools.py::load_receipt_bytes``), so an unrecognised
    suffix is rejected rather than silently stored.
    """
    base_name = Path(filename or "").name
    suffix = Path(base_name).suffix.lower()
    if suffix not in RECEIPT_SUFFIXES:
        raise UnsupportedReceiptError(suffix or base_name)
    stored_name = f"{uuid.uuid4().hex[:12]}{suffix}"
    dest = receipt_storage_dir() / stored_name
    dest.write_bytes(content)
    return dest


def resolve_stored_receipt(stored_name: str) -> Path | None:
    """Map a stored file name back to a path, refusing anything traversal-like."""
    if not _STORED_NAME.match(stored_name or ""):
        return None
    candidate = (receipt_storage_dir() / stored_name).resolve()
    if candidate.parent != receipt_storage_dir().resolve():
        return None
    return candidate if candidate.is_file() else None


class UnsupportedReceiptError(Exception):
    def __init__(self, suffix: str) -> None:
        super().__init__(
            f"Unsupported receipt type '{suffix}'. "
            f"Allowed: {', '.join(sorted(RECEIPT_SUFFIXES))}"
        )
        self.code = "unsupported_receipt_type"


def store_pdf(filename: str, content: bytes) -> Path:
    into = policy_storage_dir()
    base_name = Path(filename).name
    if not base_name or base_name in {".", ".."}:
        base_name = "policy.pdf"
    if Path(base_name).suffix.lower() != ".pdf":
        base_name = f"{base_name}.pdf"
    stored_name = f"{uuid.uuid4().hex[:12]}_{base_name}"
    dest = into / stored_name
    dest.write_bytes(content)
    return dest