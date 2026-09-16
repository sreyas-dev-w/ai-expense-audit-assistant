from datetime import date, datetime, timezone
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.employee_repository import EmployeeRepository
from app.schemas.extraction import (
    EmployeeContext,
    FoodMealsDetails,
    TravelDetails,
    AccommodationDetails,
    OtherDetails,
    OCRResponse,
    Submission,
)
from app.services.ocr_extraction_gemini_service import GeminiService


class OCRState(TypedDict, total=False):
    """State object for the OCR workflow"""

    employee_id: str
    expense_category: str
    spend_amount: Optional[float]
    business_purpose: Optional[str]
    meal_type: Optional[str]
    number_of_people: Optional[int]
    travel_type: Optional[str]
    origin: Optional[str]
    destination: Optional[str]
    travel_class: Optional[str]
    location: Optional[str]
    check_in_date: Optional[date]
    check_out_date: Optional[date]
    number_of_days: Optional[int]
    room_type: Optional[str]
    expense_type: Optional[str]
    additional_details: Optional[str]
    receipt_bytes: Optional[bytes]
    mime_type: Optional[str]

    employee: Optional[dict]
    project: Optional[dict]
    employee_context: Optional[EmployeeContext]
    submission: Optional[Submission]
    extraction: Optional[dict]
    details: Optional[dict]


class OCRAgent:

    def __init__(self, session: AsyncSession = None):
        self.session = session
        self.employee_repository = EmployeeRepository(session)
        self.gemini_service = GeminiService()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(OCRState)

        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("fetch_employee", self._fetch_employee)
        workflow.add_node("fetch_project", self._fetch_project)
        workflow.add_node("validate_category_specific", self._validate_category_specific)
        workflow.add_node("create_submission", self._create_submission)
        workflow.add_node("extract_receipt", self._extract_receipt)
        workflow.add_node("create_response", self._create_response)

        workflow.add_edge(START, "validate_input")
        workflow.add_edge("validate_input", "fetch_employee")
        workflow.add_edge("fetch_employee", "fetch_project")
        workflow.add_edge("fetch_project", "validate_category_specific")
        workflow.add_edge("validate_category_specific", "create_submission")
        workflow.add_edge("create_submission", "extract_receipt")
        workflow.add_edge("extract_receipt", "create_response")
        workflow.add_edge("create_response", END)

        return workflow.compile()

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
        employee: dict | None = None,
        project: dict | None = None,
    ) -> OCRResponse:
        """Process OCR extraction through LangGraph workflow"""

        initial_state: OCRState = {
            "employee_id": employee_id,
            "expense_category": expense_category,
            "spend_amount": spend_amount,
            "business_purpose": business_purpose,
            "meal_type": meal_type,
            "number_of_people": number_of_people,
            "travel_type": travel_type,
            "origin": origin,
            "destination": destination,
            "travel_class": travel_class,
            "location": location,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "number_of_days": number_of_days,
            "room_type": room_type,
            "expense_type": expense_type,
            "additional_details": additional_details,
            "receipt_bytes": receipt_bytes,
            "mime_type": mime_type,
        }
        if employee is not None:
            initial_state["employee"] = employee
        if project is not None:
            initial_state["project"] = project

        result = await self.graph.ainvoke(initial_state)
        return result["response"]

    async def _validate_input(self, state: OCRState) -> OCRState:
        """Validate common input parameters"""

        employee_id = state.get("employee_id")
        if employee_id is None:
            print("[OCR VALIDATION ERROR] Employee ID is required.")
            raise ValueError("Employee ID is required.")

        employee_id = employee_id.strip()
        if not employee_id:
            print("[OCR VALIDATION ERROR] Employee ID is required.")
            raise ValueError("Employee ID is required.")

        state["employee_id"] = employee_id

        expense_category = state.get("expense_category")
        if expense_category is None:
            print("[OCR VALIDATION ERROR] Expense category is required.")
            raise ValueError("Expense category is required.")

        expense_category = expense_category.strip().upper()

        allowed_categories = {"FOOD_MEALS", "TRAVEL", "ACCOMMODATION", "OTHERS"}
        if expense_category not in allowed_categories:
            print(f"[OCR VALIDATION ERROR] Invalid expense category: {expense_category}")
            raise ValueError(
                "Invalid expense category. "
                "Allowed categories are "
                "FOOD_MEALS, TRAVEL, ACCOMMODATION, OTHERS."
            )

        state["expense_category"] = expense_category

        receipt_bytes = state.get("receipt_bytes")
        if not receipt_bytes:
            print("[OCR VALIDATION ERROR] Receipt file is required.")
            raise ValueError("Receipt file is required.")

        mime_type = state.get("mime_type")
        allowed_mime_types = {"image/jpeg", "image/png", "application/pdf"}

        if mime_type is None:
            print("[OCR VALIDATION ERROR] Receipt format is required.")
            raise ValueError("Receipt format is required.")

        if mime_type not in allowed_mime_types:
            print(f"[OCR VALIDATION ERROR] Unsupported receipt format: {mime_type}.")
            raise ValueError(
                f"Unsupported receipt format: {mime_type}. "
                "Supported formats are PNG, JPEG, and PDF."
            )

        print("[OCR] Common input validation passed.")
        return state

    async def _fetch_employee(self, state: OCRState) -> OCRState:
        """Fetch employee from database"""

        if state.get("employee"):
            print("[OCR] Using preloaded employee context.")
            return state

        employee_id = state["employee_id"]
        employee = await self.employee_repository.get_employee(employee_id)

        if employee is None:
            print(f"[OCR ERROR] Employee ID '{employee_id}' was not found.")
            raise ValueError(f"Employee ID '{employee_id}' does not exist.")

        print(f"[OCR] Employee '{employee_id}' found.")
        state["employee"] = employee
        return state

    async def _fetch_project(self, state: OCRState) -> OCRState:
        """Fetch project and create employee context"""

        employee = state["employee"]
        employee_id = state["employee_id"]

        project = None
        account_id = None

        if employee.get("project_code"):
            if state.get("project") is None:
                project = await self.employee_repository.get_project(
                    employee["project_code"]
                )
            else:
                project = state.get("project")

        if project:
            account_id = project.get("account_id")
            print(f"[OCR] Project '{employee['project_code']}' found.")
        else:
            print(f"[OCR WARNING] Project '{employee['project_code']}' was not found.")

        state["project"] = project

        employee_context = EmployeeContext(
            employee_id=employee_id,
            found=True,
            employee_name=employee["employee_name"],
            job_level=employee["job_level"],
            manager_id=employee["manager_id"],
            project_code=employee["project_code"],
            account_id=account_id,
        )

        state["employee_context"] = employee_context
        return state

    async def _validate_category_specific(self, state: OCRState) -> OCRState:
        """Validate category-specific parameters"""

        expense_category = state["expense_category"]
        spend_amount = state.get("spend_amount")
        meal_type = state.get("meal_type")
        number_of_people = state.get("number_of_people")
        travel_type = state.get("travel_type")
        origin = state.get("origin")
        destination = state.get("destination")
        travel_class = state.get("travel_class")
        location = state.get("location")
        check_in_date = state.get("check_in_date")
        check_out_date = state.get("check_out_date")
        number_of_days = state.get("number_of_days")
        room_type = state.get("room_type")
        expense_type = state.get("expense_type")
        additional_details = state.get("additional_details")
        business_purpose = state.get("business_purpose")

        details = None

        if expense_category == "FOOD_MEALS":
            if spend_amount is None:
                raise ValueError("Spend amount is required for FOOD_MEALS.")

            try:
                spend_amount = float(spend_amount)
            except (TypeError, ValueError):
                raise ValueError("Spend amount must be a valid number.")

            if spend_amount <= 0:
                raise ValueError("Spend amount must be greater than 0.")

            if meal_type is None:
                raise ValueError("Meal type is required for FOOD_MEALS.")

            meal_type = meal_type.strip().upper()

            if meal_type not in {"VEG", "NON_VEG", "MIXED"}:
                raise ValueError("Meal type must be VEG, NON_VEG, or MIXED.")

            if number_of_people is None:
                raise ValueError("Number of people is required for FOOD_MEALS.")

            if number_of_people <= 0:
                raise ValueError("Number of people must be greater than 0.")

            details = FoodMealsDetails(
                expense_category="FOOD_MEALS",
                spend_amount=spend_amount,
                business_purpose=business_purpose,
                meal_type=meal_type,
                number_of_people=number_of_people,
            )

        elif expense_category == "TRAVEL":
            if spend_amount is None:
                raise ValueError("Spend amount is required for TRAVEL.")

            try:
                spend_amount = float(spend_amount)
            except (TypeError, ValueError):
                raise ValueError("Spend amount must be a valid number.")

            if spend_amount <= 0:
                raise ValueError("Spend amount must be greater than 0.")

            if not travel_type:
                raise ValueError("Travel type is required for TRAVEL.")

            travel_type = travel_type.strip().upper()

            if travel_type not in {"FLIGHT", "TRAIN", "BUS", "CAR", "BIKE"}:
                raise ValueError("Invalid travel type.")

            if not origin or not origin.strip():
                raise ValueError("Origin is required for TRAVEL.")

            if not destination or not destination.strip():
                raise ValueError("Destination is required for TRAVEL.")

            if not travel_class:
                raise ValueError("Travel class is required for TRAVEL.")

            travel_class = travel_class.strip().upper()

            if travel_class not in {"BUSINESS_CLASS", "ECONOMY_CLASS"}:
                raise ValueError("Travel class must be BUSINESS_CLASS or ECONOMY_CLASS.")

            details = TravelDetails(
                expense_category="TRAVEL",
                spend_amount=spend_amount,
                travel_type=travel_type,
                origin=origin.strip(),
                destination=destination.strip(),
                travel_class=travel_class,
                business_purpose=business_purpose,
            )

        elif expense_category == "ACCOMMODATION":
            if spend_amount is None:
                raise ValueError("Spend amount is required for ACCOMMODATION.")

            try:
                spend_amount = float(spend_amount)
            except (TypeError, ValueError):
                raise ValueError("Spend amount must be a valid number.")

            if spend_amount <= 0:
                raise ValueError("Spend amount must be greater than 0.")

            if not location or not location.strip():
                raise ValueError("Location is required for ACCOMMODATION.")

            if check_in_date is None:
                raise ValueError("Check-in date is required.")

            if check_out_date is None:
                raise ValueError("Check-out date is required.")

            if check_out_date <= check_in_date:
                raise ValueError("Check-out date must be after check-in date.")

            calculated_days = (check_out_date - check_in_date).days

            if number_of_days is not None:
                if number_of_days != calculated_days:
                    raise ValueError(
                        "Number of days does not match "
                        "the selected check-in and check-out dates."
                    )

            number_of_days = calculated_days

            if not room_type or not room_type.strip():
                raise ValueError("Room type is required for ACCOMMODATION.")

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

        else:
            if spend_amount is None:
                raise ValueError("Spend amount is required for OTHERS.")

            try:
                spend_amount = float(spend_amount)
            except (TypeError, ValueError):
                raise ValueError("Spend amount must be a valid number.")

            if spend_amount <= 0:
                raise ValueError("Spend amount must be greater than 0.")

            if not expense_type or not expense_type.strip():
                raise ValueError("Expense type is required for OTHERS.")

            details = OtherDetails(
                expense_category="OTHERS",
                spend_amount=spend_amount,
                business_purpose=business_purpose,
                expense_type=expense_type.strip(),
                additional_details=additional_details,
            )

        print(f"[OCR] Category-specific validation passed for '{expense_category}'.")
        state["details"] = details
        return state

    async def _create_submission(self, state: OCRState) -> OCRState:
        """Create submission object"""

        submission = Submission(
            employee_id=state["employee_id"],
            expense_category=state["expense_category"],
            details=state["details"],
            submitted_at=datetime.now(timezone.utc),
            receipt_provided=True,
        )

        print("[OCR] Submission metadata created.")
        state["submission"] = submission
        return state

    async def _extract_receipt(self, state: OCRState) -> OCRState:
        """Extract receipt using Gemini"""

        expense_category = state["expense_category"]
        employee_id = state["employee_id"]
        receipt_bytes = state["receipt_bytes"]
        mime_type = state["mime_type"]

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

        state["extraction"] = extraction
        return state

    async def _create_response(self, state: OCRState) -> OCRState:
        """Create final OCR response"""
        state["response"] = OCRResponse(
            submission=state["submission"],
            employee_context=state["employee_context"],
            extraction=state["extraction"],
        )
        return state