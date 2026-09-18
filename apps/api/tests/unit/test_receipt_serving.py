"""Unit tests for stored-receipt resolution and the receipts serving route."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.receipts import router
from app.services import file_service


@pytest.fixture
def receipt_under_root(tmp_path, monkeypatch):
    """Point storage at a temp layout matching the real (apps/api) one."""
    root = tmp_path / "app"
    storage_dir = root / "storage_dump" / "receipts"
    storage_dir.mkdir(parents=True)

    monkeypatch.setattr(file_service, "app_root_dir", lambda: root)
    monkeypatch.setattr(
        file_service.settings, "receipt_storage_dir", Path("storage_dump/receipts")
    )

    receipt = storage_dir / "a1b2c3d4e5f6_receipt.jpg"
    receipt.write_bytes(b"fake-jpeg-bytes")
    return root, storage_dir, receipt


def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_resolves_relative_receipt_path(receipt_under_root):
    root, storage_dir, receipt = receipt_under_root
    resolved = file_service.resolve_receipt_path("storage_dump/receipts/a1b2c3d4e5f6_receipt.jpg")
    assert resolved == receipt.resolve()


def test_resolves_absolute_path_inside_storage(receipt_under_root):
    root, storage_dir, receipt = receipt_under_root
    resolved = file_service.resolve_receipt_path(str(receipt.resolve()))
    assert resolved == receipt.resolve()


def test_rejects_missing_receipt(receipt_under_root):
    with pytest.raises(FileNotFoundError):
        file_service.resolve_receipt_path("storage_dump/receipts/does-not-exist.jpg")


def test_rejects_path_escape(receipt_under_root):
    with pytest.raises(ValueError):
        file_service.resolve_receipt_path("storage_dump/receipts/../../outside.jpg")


def test_rejects_absolute_path_outside_storage(receipt_under_root, tmp_path):
    outside = tmp_path / "outside" / "receipt.jpg"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"x")
    with pytest.raises(ValueError):
        file_service.resolve_receipt_path(str(outside.resolve()))


def test_rejects_http_url(receipt_under_root):
    with pytest.raises(ValueError):
        file_service.resolve_receipt_path("https://example.com/receipt.jpg")


def test_rejects_empty_path(receipt_under_root):
    with pytest.raises(ValueError):
        file_service.resolve_receipt_path("   ")


def test_route_serves_receipt(receipt_under_root):
    response = client().get("/api/v1/receipts/storage_dump/receipts/a1b2c3d4e5f6_receipt.jpg")
    assert response.status_code == 200
    assert response.content == b"fake-jpeg-bytes"


def test_route_rejects_traversal(receipt_under_root):
    response = client().get(
        "/api/v1/receipts/storage_dump/receipts/../../outside.jpg"
    )
    assert response.status_code == 400


def test_route_returns_404_for_missing_receipt(receipt_under_root):
    response = client().get("/api/v1/receipts/storage_dump/receipts/nope.jpg")
    assert response.status_code == 404