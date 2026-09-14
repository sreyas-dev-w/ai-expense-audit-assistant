from datetime import datetime, timezone

from app.agents.ocr_extraction.employee_repository import EmployeeRepository
from app.agents.ocr_extraction.schemas import (
    EmployeeContext,
    OCRResponse,
    Receipt,
    Submission,
)
from app.agents.ocr_extraction.services.gemini_service import GeminiService
from app.agents.ocr_extraction.services.receipt_service import ReceiptService


class OCRAgent:

    def __init__(self):
        self.employee_repository = EmployeeRepository()
        self.receipt_service = ReceiptService()
        self.gemini_service = GeminiService()

    async def process(
        self,
        employee_id: str,
        declared_category: str,
        spend_amount: float,
        business_purpose: str | None,
        receipt_bytes: bytes,
        mime_type: str,
    ) -> OCRResponse:

        # ==================================================
        # 0. Validate input
        # ==================================================

        # Employee ID
        if employee_id is None:
            print("[OCR VALIDATION ERROR] Employee ID is required.")
            raise ValueError("Employee ID is required.")

        employee_id = employee_id.strip()

        if not employee_id:
            print("[OCR VALIDATION ERROR] Employee ID is required.")
            raise ValueError("Employee ID is required.")

        # Spend category
        if declared_category is None:
            print("[OCR VALIDATION ERROR] Spend category is required.")
            raise ValueError("Spend category is required.")

        declared_category = declared_category.strip()

        if not declared_category:
            print("[OCR VALIDATION ERROR] Spend category is required.")
            raise ValueError("Spend category is required.")

        # Spend amount
        if spend_amount is None:
            print("[OCR VALIDATION ERROR] Spend amount is required.")
            raise ValueError("Spend amount is required.")

        try:
            spend_amount = float(spend_amount)
        except (TypeError, ValueError):
            print(
                "[OCR VALIDATION ERROR] "
                "Spend amount must be a valid number."
            )
            raise ValueError(
                "Spend amount must be a valid number."
            )

        if spend_amount <= 0:
            print(
                "[OCR VALIDATION ERROR] "
                "Spend amount must be greater than 0."
            )
            raise ValueError(
                "Spend amount must be greater than 0."
            )

        # Business purpose
        if business_purpose is not None:
            business_purpose = business_purpose.strip()

            if not business_purpose:
                business_purpose = None

        # Receipt
        if not receipt_bytes:
            print(
                "[OCR VALIDATION ERROR] "
                "Receipt file is required."
            )
            raise ValueError(
                "Receipt file is required."
            )

        # MIME type
        allowed_mime_types = {
            "image/jpeg",
            "image/png",
            "application/pdf",
        }

        if mime_type is None:
            print(
                "[OCR VALIDATION ERROR] "
                "Receipt format is required."
            )
            raise ValueError(
                "Receipt format is required."
            )

        if mime_type not in allowed_mime_types:
            print(
                f"[OCR VALIDATION ERROR] "
                f"Unsupported receipt format: {mime_type}. "
                "Supported formats are PNG, JPEG, and PDF."
            )

            raise ValueError(
                f"Unsupported receipt format: {mime_type}. "
                "Supported formats are PNG, JPEG, and PDF."
            )

        print("[OCR] Input validation passed.")

        # ==================================================
        # 1. Validate employee ID
        # ==================================================

        employee = self.employee_repository.get_employee(
            employee_id
        )

        if employee is None:
            print(
                f"[OCR ERROR] Employee ID '{employee_id}' "
                "was not found in the employee repository."
            )

            # Gemini will NOT be called.
            raise ValueError(
                f"Employee ID '{employee_id}' does not exist."
            )

        print(
            f"[OCR] Employee '{employee_id}' found."
        )

        # ==================================================
        # 2. Fetch project
        # ==================================================

        project = self.employee_repository.get_project(
            employee["project_code"]
        )

        account_id = None

        if project:
            account_id = project["account_id"]

            print(
                f"[OCR] Project '{employee['project_code']}' "
                "found."
            )

        else:
            print(
                f"[OCR WARNING] Project "
                f"'{employee['project_code']}' was not found."
            )

        # ==================================================
        # 3. Build employee context
        # ==================================================

        employee_context = EmployeeContext(
            employee_id=employee_id,
            found=True,
            employee_name=employee["employee_name"],
            job_level=employee["job_level"],
            manager_id=employee["manager_id"],
            project_code=employee["project_code"],
            account_id=account_id,
        )

        # ==================================================
        # 4. Receipt metadata
        # ==================================================

        receipt_metadata = self.receipt_service.generate_metadata(
            receipt_bytes
        )

        receipt = Receipt(
            sha256=receipt_metadata["sha256"],
        )

        print("[OCR] Receipt metadata generated.")

        # ==================================================
        # 5. Submission metadata
        # ==================================================

        submission = Submission(
            employee_id=employee_id,
            declared_category=declared_category,
            business_purpose=business_purpose,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            receipt_provided=True,
        )

        print("[OCR] Submission metadata created.")

        # ==================================================
        # 6. Gemini receipt extraction
        # ==================================================

        print(
            f"[OCR] Sending receipt to Gemini "
            f"for employee '{employee_id}'."
        )

        extraction = await self.gemini_service.extract_receipt(
            receipt_bytes=receipt_bytes,
            mime_type=mime_type,
        )

        print(
            f"[OCR] Receipt extraction completed "
            f"for employee '{employee_id}'."
        )

        # ==================================================
        # 7. Return OCR response
        # ==================================================

        return OCRResponse(
            submission=submission,
            employee_context=employee_context,
            receipt=receipt,
            extraction=extraction,
        )