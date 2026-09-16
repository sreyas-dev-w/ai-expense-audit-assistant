"""Development data store. Replace with repository/MySQL implementations later."""

from datetime import datetime, timezone
from itertools import count

USERS = {
    "aarav.sharma@example.com": {
        "user_id": "USR-001",
        "employee_id": "EMP-001",
        "name": "Aarav Sharma",
        "department": "Engineering",
        "country": "India",
        "role": "EMPLOYEE",
        "password": "Demo@123",
        "active": True,
    },
    "auditor@example.com": {
        "user_id": "USR-010",
        "employee_id": "EMP-010",
        "name": "Finance Auditor",
        "department": "Finance",
        "country": "India",
        "role": "AUDITOR",
        "password": "Demo@123",
        "active": True,
    },
    "admin@example.com": {
        "user_id": "USR-999",
        "employee_id": "EMP-999",
        "name": "System Admin",
        "department": "Finance",
        "country": "India",
        "role": "ADMIN",
        "password": "Demo@123",
        "active": True,
    },
}
documents: dict[str, dict] = {}
policies: dict[str, dict] = {}
claims: dict[str, dict] = {}
audits: dict[str, dict] = {}
document_numbers, policy_numbers, claim_numbers, audit_numbers = count(1), count(1), count(1), count(1)


def identifier(prefix: str, sequence) -> str:
    return f"{prefix}-{next(sequence):04d}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
