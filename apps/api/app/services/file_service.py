"""Filesystem storage for uploaded policy documents.

Files land in a backend-local dump directory ("storage_dump/policies" under
``apps/api`` by default, configurable via ``POLICY_STORAGE_DIR``). Stored file
names are prefixed with a random id so repeated uploads never collide while
keeping the original base name for traceability.
"""
import uuid
from pathlib import Path

from app.core.config import settings


def policy_storage_dir() -> Path:
    base = Path(__file__).resolve().parents[2]
    path = settings.policy_storage_dir
    resolved = base / path if not path.is_absolute() else path
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


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