EMPLOYEES = {
    "EMP-018": {
        "employee_id": "EMP-018",
        "employee_name": "Bhavna Singh",
        "job_level": "L2",
        "manager_id": "EMP-003",
        "project_code": "CAPSTONE-001",
    },
    "EMP-003": {
        "employee_id": "EMP-003",
        "employee_name": "Arun Kumar",
        "job_level": "L3",
        "manager_id": "EMP-001",
        "project_code": "CAPSTONE-001",
    },
}


PROJECTS = {
    "CAPSTONE-001": {
        "account_id": "ACC-001",
        "project_name": "Capstone Demo",
        "project_code": "CAPSTONE-001",
        "project_lead_id": "EMP-003",
    },
}


ACCOUNTS = {
    "ACC-001": {
        "account_id": "ACC-001",
        "account_name": "Capstone Engineering",
        "fiscal_year": 2026,
        "budget_allocated": 500000.00,
        "spent_amount": 125000.00,
        "remaining_budget": 375000.00,
        "currency": "INR",
    },
}


class EmployeeRepository:
    """In-memory repository matching the async production interface."""

    def __init__(self, session: object | None = None) -> None:
        # Accept the production constructor argument so this repository can be
        # substituted without changing OCRAgent. No session is needed in-memory.
        self.session = session

    async def get_employee(self, employee_id: str):
        return EMPLOYEES.get(employee_id)

    async def get_project(self, project_code: str):
        return PROJECTS.get(project_code)

    async def get_account(self, account_id: str):
        return ACCOUNTS.get(account_id)
