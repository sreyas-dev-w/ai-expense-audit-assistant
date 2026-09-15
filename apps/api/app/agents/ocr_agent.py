from datetime import date, datetime, timezone

from api.tests.evaluation.test_employee_repository import EmployeeRepository
from app.schemas.extraction import (
    EmployeeContext,
    Extraction,
    FoodMealsDetails,
    TravelDetails,
    AccommodationDetails,
    OtherDetails,
    OCRResponse,
    Submission,
)
from app.services.ocr_extraction_gemini_service import GeminiService


class OCRAgent:

    def __init__(self):
        self.employee_repository = EmployeeRepository()
        self.gemini_service = GeminiService()

    async def process(
        self,
        employee_id: str,
        expense_category: str,

        spend_amount: float | None = None,
        business_purpose: str | None = None,

        # FOOD_MEALS
        meal_type: str | None = None,
        number_of_people: int | None = None,

        # TRAVEL
        travel_type: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        travel_class: str | None = None,

        # ACCOMMODATION
        location: str | None = None,
        check_in_date: date | None = None,
        check_out_date: date | None = None,
        number_of_days: int | None = None,
        room_type: str | None = None,

        # OTHERS
        expense_type: str | None = None,
        additional_details: str | None = None,

        # RECEIPT
        receipt_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> OCRResponse:

        # ==================================================
        # 0. COMMON VALIDATION
        # ==================================================

        if employee_id is None:
            print("[OCR VALIDATION ERROR] Employee ID is required.")
            raise ValueError("Employee ID is required.")

        employee_id = employee_id.strip()

        if not employee_id:
            print("[OCR VALIDATION ERROR] Employee ID is required.")
            raise ValueError("Employee ID is required.")

        # --------------------------------------------------
        # Expense category
        # --------------------------------------------------

        if expense_category is None:
            print(
                "[OCR VALIDATION ERROR] "
                "Expense category is required."
            )
            raise ValueError("Expense category is required.")

        expense_category = expense_category.strip().upper()

        allowed_categories = {
            "FOOD_MEALS",
            "TRAVEL",
            "ACCOMMODATION",
            "OTHERS",
        }

        if expense_category not in allowed_categories:
            print(
                f"[OCR VALIDATION ERROR] "
                f"Invalid expense category: {expense_category}"
            )

            raise ValueError(
                "Invalid expense category. "
                "Allowed categories are "
                "FOOD_MEALS, TRAVEL, ACCOMMODATION, OTHERS."
            )

        # --------------------------------------------------
        # Receipt
        # --------------------------------------------------

        if not receipt_bytes:
            print(
                "[OCR VALIDATION ERROR] "
                "Receipt file is required."
            )
            raise ValueError("Receipt file is required.")

        # --------------------------------------------------
        # MIME type
        # --------------------------------------------------

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
            raise ValueError("Receipt format is required.")

        if mime_type not in allowed_mime_types:
            print(
                f"[OCR VALIDATION ERROR] "
                f"Unsupported receipt format: {mime_type}."
            )

            raise ValueError(
                f"Unsupported receipt format: {mime_type}. "
                "Supported formats are PNG, JPEG, and PDF."
            )

        print("[OCR] Common input validation passed.")

        # ==================================================
        # 1. CATEGORY-SPECIFIC VALIDATION
        # ==================================================

        # ==================================================
        # FOOD_MEALS
        # ==================================================

        if expense_category == "FOOD_MEALS":

            if spend_amount is None:
                raise ValueError(
                    "Spend amount is required for FOOD_MEALS."
                )

            try:
                spend_amount = float(spend_amount)
            except (TypeError, ValueError):
                raise ValueError(
                    "Spend amount must be a valid number."
                )

            if spend_amount <= 0:
                raise ValueError(
                    "Spend amount must be greater than 0."
                )

            if meal_type is None:
                raise ValueError(
                    "Meal type is required for FOOD_MEALS."
                )

            meal_type = meal_type.strip().upper()

            if meal_type not in {
                "VEG",
                "NON_VEG",
                "MIXED",
            }:
                raise ValueError(
                    "Meal type must be VEG, NON_VEG, or MIXED."
                )

            if number_of_people is None:
                raise ValueError(
                    "Number of people is required for FOOD_MEALS."
                )

            if number_of_people <= 0:
                raise ValueError(
                    "Number of people must be greater than 0."
                )

            details = FoodMealsDetails(
                expense_category="FOOD_MEALS",
                spend_amount=spend_amount,
                business_purpose=business_purpose,
                meal_type=meal_type,
                number_of_people=number_of_people,
            )

        # ==================================================
        # TRAVEL
        # ==================================================

        elif expense_category == "TRAVEL":

            if spend_amount is None:
                raise ValueError(
                    "Spend amount is required for TRAVEL."
                )

            try:
                spend_amount = float(spend_amount)
            except (TypeError, ValueError):
                raise ValueError(
                    "Spend amount must be a valid number."
                )

            if spend_amount <= 0:
                raise ValueError(
                    "Spend amount must be greater than 0."
                )

            if not travel_type:
                raise ValueError(
                    "Travel type is required for TRAVEL."
                )

            travel_type = travel_type.strip().upper()

            if travel_type not in {
                "FLIGHT",
                "TRAIN",
                "BUS",
                "CAR",
                "BIKE",
            }:
                raise ValueError(
                    "Invalid travel type."
                )

            if not origin or not origin.strip():
                raise ValueError(
                    "Origin is required for TRAVEL."
                )

            if not destination or not destination.strip():
                raise ValueError(
                    "Destination is required for TRAVEL."
                )

            if not travel_class:
                raise ValueError(
                    "Travel class is required for TRAVEL."
                )

            travel_class = travel_class.strip().upper()

            if travel_class not in {
                "BUSINESS_CLASS",
                "ECONOMY_CLASS",
            }:
                raise ValueError(
                    "Travel class must be BUSINESS_CLASS "
                    "or ECONOMY_CLASS."
                )

            details = TravelDetails(
                expense_category="TRAVEL",
                spend_amount=spend_amount,
                travel_type=travel_type,
                origin=origin.strip(),
                destination=destination.strip(),
                travel_class=travel_class,
                business_purpose=business_purpose,
            )

        # ==================================================
        # ACCOMMODATION
        # ==================================================

        elif expense_category == "ACCOMMODATION":

            if spend_amount is None:
                raise ValueError(
                    "Spend amount is required for ACCOMMODATION."
                )

            try:
                spend_amount = float(spend_amount)
            except (TypeError, ValueError):
                raise ValueError(
                    "Spend amount must be a valid number."
                )

            if spend_amount <= 0:
                raise ValueError(
                    "Spend amount must be greater than 0."
                )

            if not location or not location.strip():
                raise ValueError(
                    "Location is required for ACCOMMODATION."
                )

            if check_in_date is None:
                raise ValueError(
                    "Check-in date is required."
                )

            if check_out_date is None:
                raise ValueError(
                    "Check-out date is required."
                )

            if check_out_date <= check_in_date:
                raise ValueError(
                    "Check-out date must be after check-in date."
                )

            # Calculate number of days from dates.
            calculated_days = (
                check_out_date - check_in_date
            ).days

            # If frontend sends number_of_days,
            # validate it against the calculated value.
            if number_of_days is not None:
                if number_of_days != calculated_days:
                    raise ValueError(
                        "Number of days does not match "
                        "the selected check-in and check-out dates."
                    )

            number_of_days = calculated_days

            if not room_type or not room_type.strip():
                raise ValueError(
                    "Room type is required for ACCOMMODATION."
                )

            details = AccommodationDetails(
                expense_category="ACCOMMODATION",
                spend_amount=spend_amount,
                business_purpose=business_purpose,
                location=location.strip(),
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                number_of_days=number_of_days,
                room_type=room_type.strip(),
            )

        # ==================================================
        # OTHERS
        # ==================================================

        else:

            if spend_amount is None:
                raise ValueError(
                    "Spend amount is required for OTHERS."
                )

            try:
                spend_amount = float(spend_amount)
            except (TypeError, ValueError):
                raise ValueError(
                    "Spend amount must be a valid number."
                )

            if spend_amount <= 0:
                raise ValueError(
                    "Spend amount must be greater than 0."
                )

            if not expense_type or not expense_type.strip():
                raise ValueError(
                    "Expense type is required for OTHERS."
                )

            details = OtherDetails(
                expense_category="OTHERS",
                spend_amount=spend_amount,
                business_purpose=business_purpose,
                expense_type=expense_type.strip(),
                additional_details=additional_details,
            )

        print(
            f"[OCR] Category-specific validation passed "
            f"for '{expense_category}'."
        )

        # ==================================================
        # 2. VALIDATE EMPLOYEE
        # ==================================================

        employee = self.employee_repository.get_employee(
            employee_id
        )

        if employee is None:
            print(
                f"[OCR ERROR] Employee ID '{employee_id}' "
                "was not found."
            )

            raise ValueError(
                f"Employee ID '{employee_id}' does not exist."
            )

        print(
            f"[OCR] Employee '{employee_id}' found."
        )

        # ==================================================
        # 3. FETCH PROJECT
        # ==================================================

        project = self.employee_repository.get_project(
            employee["project_code"]
        )

        account_id = None

        if project:
            account_id = project["account_id"]

            print(
                f"[OCR] Project '{employee['project_code']}' found."
            )

        else:
            print(
                f"[OCR WARNING] Project "
                f"'{employee['project_code']}' was not found."
            )

        # ==================================================
        # 4. EMPLOYEE CONTEXT
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
        # 5. SUBMISSION
        # ==================================================

        submission = Submission(
            employee_id=employee_id,
            expense_category=expense_category,
            details=details,
            submitted_at=datetime.now(timezone.utc),
            receipt_provided=True,
        )

        print(
            "[OCR] Submission metadata created."
        )

        # ==================================================
        # 6. GEMINI RECEIPT EXTRACTION
        # ==================================================

        print(
            f"[OCR] Sending {expense_category} receipt "
            f"to Gemini for employee '{employee_id}'."
        )

        extraction = await self.gemini_service.extract_receipt(
            receipt_bytes=receipt_bytes,
            mime_type=mime_type,
            expense_category=expense_category,
        )

        print(
            f"[OCR] Receipt extraction completed "
            f"for employee '{employee_id}'."
        )

        # ==================================================
        # 7. FINAL RESPONSE
        # ==================================================

        return OCRResponse(
            submission=submission,
            employee_context=employee_context,
            extraction=extraction,
        )