import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("GEMINI_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.services.api_store import audits, claims, documents, policies


class ContractApiTests(unittest.TestCase):
    """Two representative tests for each public API in the contract."""

    def setUp(self) -> None:
        documents.clear()
        policies.clear()
        claims.clear()
        audits.clear()
        self.client = TestClient(app)
        self.mkdir_patch = patch.object(Path, "mkdir")
        self.write_patch = patch.object(Path, "write_bytes")
        self.mkdir_patch.start()
        self.write_patch.start()
        self.addCleanup(self.mkdir_patch.stop)
        self.addCleanup(self.write_patch.stop)
        self.addCleanup(self.client.close)

    def token_for(self, username: str) -> str:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "Demo@123"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    def headers_for(self, username: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token_for(username)}"}

    def seed_policy(self, *, country: str = "India") -> None:
        policies["POL-TEST"] = {
            "policy_id": "POL-TEST",
            "policy_name": "Expense Policy",
            "policy_version": "EXPENSE-POLICY-V1",
            "effective_from": "2026-01-01",
            "country": country,
            "active": True,
            "indexing_status": "READY",
        }

    def seed_receipt(self) -> None:
        documents["DOC-TEST"] = {
            "document_id": "DOC-TEST",
            "document_type": "RECEIPT",
            "original_filename": "receipt.jpg",
            "owner_id": "USR-001",
            "upload_status": "UPLOADED",
        }

    @staticmethod
    def claim_body() -> dict:
        return {
            "policy_version": "EXPENSE-POLICY-V1",
            "purpose": "Client meeting travel",
            "project_code": "CAPSTONE-001",
            "expense_lines": [
                {
                    "expense_date": "2026-09-05",
                    "expense_category": "MEALS",
                    "merchant_name": "The Food Court",
                    "claimed_amount": "2400.00",
                    "currency": "INR",
                    "description": "Client dinner",
                    "receipt_document_id": "DOC-TEST",
                }
            ],
        }

    def create_claim(self) -> tuple[str, dict[str, str]]:
        self.seed_policy()
        self.seed_receipt()
        headers = self.headers_for("aarav.sharma@example.com")
        response = self.client.post(
            "/api/v1/claims",
            headers=headers,
            json=self.claim_body(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["claim_id"], headers

    # 1. Login API
    def test_login_returns_bearer_token(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "aarav.sharma@example.com", "password": "Demo@123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token_type"], "bearer")
        self.assertEqual(response.json()["user"]["role"], "EMPLOYEE")

    def test_login_rejects_invalid_password(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "aarav.sharma@example.com", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 401)

    # 2. Health API
    def test_health_returns_service_state(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertEqual(response.json()["api"], "up")

    def test_health_does_not_require_authentication(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("WWW-Authenticate", response.headers)

    # 3. Document Upload API
    def test_upload_accepts_receipt_image(self) -> None:
        response = self.client.post(
            "/api/v1/uploads",
            headers=self.headers_for("aarav.sharma@example.com"),
            data={"document_type": "RECEIPT"},
            files={"file": ("receipt.jpg", b"image-bytes", "image/jpeg")},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["document_type"], "RECEIPT")
        self.assertEqual(len(response.json()["sha256_hash"]), 64)

    def test_upload_rejects_unsupported_extension(self) -> None:
        response = self.client.post(
            "/api/v1/uploads",
            headers=self.headers_for("aarav.sharma@example.com"),
            data={"document_type": "RECEIPT"},
            files={"file": ("receipt.txt", b"text", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)

    # 4. Policy Upload API
    def test_admin_uploads_ready_policy(self) -> None:
        response = self.client.post(
            "/api/v1/policies",
            headers=self.headers_for("admin@example.com"),
            data={
                "policy_name": "Employee Expense Policy",
                "policy_version": "EXPENSE-POLICY-V1",
                "effective_from": "2026-01-01",
                "country": "India",
            },
            files={"file": ("policy.pdf", b"%PDF-test", "application/pdf")},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["indexing_status"], "READY")

    def test_employee_cannot_upload_policy(self) -> None:
        response = self.client.post(
            "/api/v1/policies",
            headers=self.headers_for("aarav.sharma@example.com"),
            data={
                "policy_name": "Employee Expense Policy",
                "policy_version": "EXPENSE-POLICY-V1",
                "effective_from": "2026-01-01",
                "country": "India",
            },
            files={"file": ("policy.pdf", b"%PDF-test", "application/pdf")},
        )
        self.assertEqual(response.status_code, 403)

    # 5. Create Claim API
    def test_employee_creates_draft_claim(self) -> None:
        claim_id, _ = self.create_claim()
        self.assertTrue(claim_id.startswith("CLM-"))
        self.assertEqual(claims[claim_id]["status"], "DRAFT")

    def test_claim_rejects_policy_for_wrong_country(self) -> None:
        self.seed_policy(country="United States")
        self.seed_receipt()
        response = self.client.post(
            "/api/v1/claims",
            headers=self.headers_for("aarav.sharma@example.com"),
            json=self.claim_body(),
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("employee country", response.json()["detail"])

    # 6. Get Claim API
    def test_employee_reads_own_claim(self) -> None:
        claim_id, headers = self.create_claim()
        response = self.client.get(f"/api/v1/claims/{claim_id}", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["claim_id"], claim_id)
        self.assertEqual(len(response.json()["expense_lines"]), 1)

    def test_employee_cannot_read_another_users_claim(self) -> None:
        claim_id, _ = self.create_claim()
        other_token = create_access_token(
            {"user_id": "USR-002", "employee_id": "EMP-002", "role": "EMPLOYEE"}
        )
        response = self.client.get(
            f"/api/v1/claims/{claim_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(response.status_code, 403)

    # 7. Submit Claim API
    def test_submit_claim_requires_no_request_body(self) -> None:
        claim_id, headers = self.create_claim()
        response = self.client.post(
            f"/api/v1/claims/{claim_id}/submit",
            headers=headers,
        )
        self.assertEqual(response.status_code, 202, response.text)
        self.assertTrue(response.json()["audit_id"].startswith("AUD-"))

    def test_submit_claim_rejects_second_submission(self) -> None:
        claim_id, headers = self.create_claim()
        first = self.client.post(f"/api/v1/claims/{claim_id}/submit", headers=headers)
        self.assertEqual(first.status_code, 202)
        second = self.client.post(f"/api/v1/claims/{claim_id}/submit", headers=headers)
        self.assertEqual(second.status_code, 409)

    # 8. Get Audit Result API
    def test_get_completed_audit_result(self) -> None:
        claim_id, headers = self.create_claim()
        self.client.post(f"/api/v1/claims/{claim_id}/submit", headers=headers)
        response = self.client.get(
            f"/api/v1/claims/{claim_id}/audit",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["audit_status"], "COMPLETED")

    def test_get_audit_rejects_unknown_claim(self) -> None:
        response = self.client.get(
            "/api/v1/claims/CLM-UNKNOWN/audit",
            headers=self.headers_for("aarav.sharma@example.com"),
        )
        self.assertEqual(response.status_code, 404)

    # 9. Auditor Decision API
    def test_admin_approves_completed_audit(self) -> None:
        claim_id, employee_headers = self.create_claim()
        submitted = self.client.post(
            f"/api/v1/claims/{claim_id}/submit",
            headers=employee_headers,
        )
        response = self.client.post(
            f"/api/v1/audits/{submitted.json()['audit_id']}/decision",
            headers=self.headers_for("admin@example.com"),
            json={"decision": "APPROVED", "comment": "Reviewed"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["final_status"], "APPROVED")

    def test_employee_cannot_make_audit_decision(self) -> None:
        claim_id, employee_headers = self.create_claim()
        submitted = self.client.post(
            f"/api/v1/claims/{claim_id}/submit",
            headers=employee_headers,
        )
        response = self.client.post(
            f"/api/v1/audits/{submitted.json()['audit_id']}/decision",
            headers=employee_headers,
            json={"decision": "REJECTED", "comment": "Not allowed"},
        )
        self.assertEqual(response.status_code, 403)

    # 10. Dashboard Summary API
    def test_admin_reads_dashboard_summary(self) -> None:
        self.create_claim()
        response = self.client.get(
            "/api/v1/dashboard/summary?department=Engineering",
            headers=self.headers_for("admin@example.com"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["summary"]["total_claims"], 1)

    def test_employee_cannot_read_dashboard(self) -> None:
        response = self.client.get(
            "/api/v1/dashboard/summary",
            headers=self.headers_for("aarav.sharma@example.com"),
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
