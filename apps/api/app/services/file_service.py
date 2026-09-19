"""Filesystem storage for uploaded documents.

Files land in backend-local dump directories under ``apps/api``
(``storage_dump/policies`` and ``storage_dump/receipts`` by default,
configurable via ``POLICY_STORAGE_DIR`` / ``RECEIPT_STORAGE_DIR``). Stored file
names are prefixed with a random id so repeated uploads never collide while
keeping the original base name for traceability.
"""
import uuid
from pathlib import Path

from app.core.config import settings

ALLOWED_RECEIPT_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "application/pdf"}
)

RECEIPT_EXTENSION_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/pdf": ".pdf",
}


def app_root_dir() -> Path:
    """Absolute backend app root (``apps/api``); base for storage dirs."""
    return Path(__file__).resolve().parents[2]


def _storage_dir(configured: Path) -> Path:
    base = app_root_dir()
    resolved = base / configured if not configured.is_absolute() else configured
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def receipt_url_from_path(stored: Path) -> str:
    """Value to persist as ``receipt_url`` for a stored receipt.

    Paths inside the app's own storage area are stored *relative to the app
    root* (e.g. ``storage_dump/receipts/….jpg``) so the persisted value is
    portable across machines and never leaks local filesystem roots. Absolute
    paths that fall outside the app storage area are kept as-is.
    """
    root = app_root_dir()
    try:
        return Path(stored).resolve().relative_to(root).as_posix()
    except ValueError:  # not under the app root — keep the caller's value
        return str(stored)


def resolve_receipt_path(receipt_url: str) -> Path:
    """Resolve a persisted ``receipt_url`` to an absolute local file path.

    Mirrors ``FetchReceiptTool._read_local``: relative values are resolved
    against the app root. Only files inside the configured receipt storage
    directory are served — anything else (path traversal escapes, absolute
    paths outside the storage area) or non-local http(s) URLs is rejected.
    """
    value = (receipt_url or "").strip()
    if not value:
        raise ValueError("Receipt URL is empty")
    if value.startswith(("http://", "https://")):
        raise ValueError("http(s) receipts are not served from local storage")

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = app_root_dir() / candidate
    resolved = candidate.resolve()

    storage_root = receipt_storage_dir().resolve()
    if resolved != storage_root and storage_root not in resolved.parents:
        raise ValueError("Receipt path resolves outside the receipt storage directory")

    if not resolved.is_file():
        raise FileNotFoundError(f"Receipt not found at {value}")
    return resolved


def policy_storage_dir() -> Path:
    return _storage_dir(settings.policy_storage_dir)


def receipt_storage_dir() -> Path:
    return _storage_dir(settings.receipt_storage_dir)


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


def store_receipt(
    filename: str, content: bytes, *, extension: str | None = None
) -> Path:
    """Persist a claim receipt and return its path (used as ``receipt_url``).

    The extension is normalized to the receipt's validated MIME type so the
    audit's ``FetchReceiptTool`` can resolve the format from the file name.
    """
    into = receipt_storage_dir()
    base_name = Path(filename).name
    if not base_name or base_name in {".", ".."}:
        base_name = "receipt"
    if extension:
        base_name = f"{Path(base_name).stem}{extension}"
    stored_name = f"{uuid.uuid4().hex[:12]}_{base_name}"
    dest = into / stored_name
    dest.write_bytes(content)
    return dest