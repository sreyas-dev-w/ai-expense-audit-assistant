"""Live Postgres tests for the one-time CSV seed loader."""
import shutil
from pathlib import Path

import pytest

from app.db.session import async_session_factory
from app.models.accounts import Account
from app.models.employees import Employee
from app.models.projects import Project
from app.repositories.seed_repository import SeedRepository
from app.services.seed_service import SeedAlreadyPopulatedError, SeedService

REPO_SEED = Path(__file__).resolve().parents[4] / "data" / "seed"


@pytest.fixture
def seed_dir(tmp_path: Path) -> Path:
    for name in ("accounts.csv", "projects.csv", "employees.csv"):
        shutil.copy(REPO_SEED / name, tmp_path / name)
    return tmp_path


@pytest.fixture
async def seeded_report(seed_dir: Path):
    return await SeedService().load_from_csv_dir(seed_dir, force=True)


async def test_seed_inserts_expected_counts(seeded_report):
    assert seeded_report.inserted.accounts == 5
    assert seeded_report.inserted.projects == 10
    assert seeded_report.inserted.employees == 61
    assert seeded_report.is_manager_count == 6
    ignored_by_file = {
        item.file: item.columns for item in seeded_report.ignored_columns
    }
    assert ignored_by_file["accounts.csv"] == ["spent_amount", "account_hr_id"]

    async with async_session_factory() as session:
        counts = await SeedRepository(session).count_rows()
    assert counts.accounts == 5
    assert counts.projects == 10
    assert counts.employees == 61


async def test_seed_spot_checks_known_rows(seeded_report):
    async with async_session_factory() as session:
        account = await session.get(Account, "ACC-001")
        project = await session.get(Project, "CAPSTONE-001")
        emp_001 = await session.get(Employee, "EMP-001")
        emp_007 = await session.get(Employee, "EMP-007")

    assert account is not None
    assert account.account_name == "Acme Corp"
    assert project is not None
    assert project.project_lead_id == "EMP-002"
    assert emp_001 is not None
    assert emp_001.is_manager is True
    assert emp_001.manager_id is None
    assert emp_007 is not None
    assert emp_007.manager_id == "EMP-002"
    assert emp_007.is_manager is False


async def test_second_seed_without_force_aborts(seeded_report, seed_dir: Path):
    with pytest.raises(SeedAlreadyPopulatedError, match="already have rows"):
        await SeedService().load_from_csv_dir(seed_dir, force=False)


async def test_dry_run_does_not_write(seeded_report, seed_dir: Path):
    async with async_session_factory() as session:
        before = await SeedRepository(session).count_rows()

    report = await SeedService().load_from_csv_dir(seed_dir, dry_run=True)
    assert report.dry_run is True
    assert report.inserted.accounts == 0
    assert report.skipped.accounts == 5
    assert report.skipped.projects == 10
    assert report.skipped.employees == 61

    async with async_session_factory() as session:
        after = await SeedRepository(session).count_rows()
    assert after == before
