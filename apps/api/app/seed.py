import csv
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, Employee, Project

_SEED_DIR = Path(__file__).resolve().parents[3] / "data" / "seed"


def _read_csv(name: str) -> list[dict[str, str]]:
    path = _SEED_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [row for row in reader]


async def seed_database(session: AsyncSession) -> None:
    """Idempotently load seed data from data/seed CSVs into the database."""

    accounts = _read_csv("accounts.csv")
    projects = _read_csv("projects.csv")
    employees = _read_csv("employees.csv")

    await session.execute(delete(Employee))
    await session.execute(delete(Project))
    await session.execute(delete(Account))
    await session.commit()

    for row in accounts:
        session.add(
            Account(
                account_id=row["account_id"],
                account_name=row["account_name"],
                fiscal_year=int(row["fiscal_year"]),
                budget_allocated=float(row["budget_allocated"]),
                spent_amount=float(row["spent_amount"]),
                remaining_budget=float(row["remaining_budget"]),
                currency=row["currency"],
                account_hr_id=row["account_hr_id"],
            )
        )

    for row in projects:
        session.add(
            Project(
                project_code=row["project_code"],
                project_name=row["project_name"],
                account_id=row["account_id"],
                project_lead_id=row["project_lead_id"],
            )
        )

    for row in employees:
        session.add(
            Employee(
                employee_id=row["employee_id"],
                employee_name=row["employee_name"],
                job_level=row["job_level"],
                manager_id=row["manager_id"] or None,
                project_code=row["project_code"],
            )
        )

    await session.commit()

    print(
        f"Seeded database: {len(accounts)} accounts, {len(projects)} projects, "
        f"{len(employees)} employees."
    )