"""Unit tests for schema-tolerant CSV seed mapping (no database)."""
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.enums import Currency, JobLevel
from app.seed.csv_mapping import (
    ACCOUNT_FIELDS,
    SeedMappingError,
    derive_is_manager,
    load_seed_tables,
    map_csv_file,
    normalize_header,
)
from app.schemas.seed import AccountSeedRow, EmployeeSeedRow, ProjectSeedRow


def _write_csv(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_normalize_header_aliases():
    assert normalize_header("account_id") == "accountid"
    assert normalize_header("Account ID") == "accountid"
    assert normalize_header("accountid") == "accountid"


def test_extra_account_columns_are_ignored(tmp_path: Path):
    path = _write_csv(
        tmp_path / "accounts.csv",
        "account_id,account_name,fiscal_year,budget_allocated,spent_amount,"
        "remaining_budget,currency,account_hr_id\n"
        "ACC-001,Acme Corp,2026,5000000,1200000,3800000,INR,HR-001\n",
    )
    mapped = map_csv_file(path, fields=ACCOUNT_FIELDS, row_model=AccountSeedRow)
    assert mapped.ignored_columns == ("spent_amount", "account_hr_id")
    assert len(mapped.rows) == 1
    row = mapped.rows[0]
    assert row.account_id == "ACC-001"
    assert row.account_name == "Acme Corp"
    assert row.fiscal_year == 2026
    assert row.budget_allocated == Decimal("5000000")
    assert row.remaining_budget == Decimal("3800000")
    assert row.currency is Currency.INR


def test_header_aliases_bind_account_fields(tmp_path: Path):
    path = _write_csv(
        tmp_path / "accounts.csv",
        "Account ID,Account Name,Fiscal Year,Budget Allocated,Remaining Budget,Currency\n"
        "ACC-001,Acme,2026,100,40,inr\n",
    )
    mapped = map_csv_file(path, fields=ACCOUNT_FIELDS, row_model=AccountSeedRow)
    assert mapped.ignored_columns == ()
    row = mapped.rows[0]
    assert row.account_id == "ACC-001"
    assert row.currency is Currency.INR


def test_compact_accountid_header_alias(tmp_path: Path):
    path = _write_csv(
        tmp_path / "accounts.csv",
        "accountid,accountname,fiscalyear,budgetallocated,remainingbudget,currency\n"
        "ACC-009,Compact,2026,1,1,USD\n",
    )
    mapped = map_csv_file(path, fields=ACCOUNT_FIELDS, row_model=AccountSeedRow)
    assert mapped.rows[0].account_id == "ACC-009"
    assert mapped.rows[0].currency is Currency.USD


def test_missing_required_columns_lists_them(tmp_path: Path):
    path = _write_csv(
        tmp_path / "accounts.csv",
        "account_id,account_name\nACC-001,Acme\n",
    )
    with pytest.raises(SeedMappingError, match="missing required columns") as exc:
        map_csv_file(path, fields=ACCOUNT_FIELDS, row_model=AccountSeedRow)
    message = str(exc.value)
    assert "fiscal_year" in message
    assert "budget_allocated" in message
    assert "remaining_budget" in message
    assert "currency" in message


def test_missing_seed_file_errors(tmp_path: Path):
    with pytest.raises(SeedMappingError, match="seed file not found"):
        map_csv_file(
            tmp_path / "accounts.csv",
            fields=ACCOUNT_FIELDS,
            row_model=AccountSeedRow,
        )


def test_invalid_enum_value(tmp_path: Path):
    path = _write_csv(
        tmp_path / "accounts.csv",
        "account_id,account_name,fiscal_year,budget_allocated,remaining_budget,currency\n"
        "ACC-001,Acme,2026,1,1,ZZZ\n",
    )
    with pytest.raises(SeedMappingError, match="currency"):
        map_csv_file(path, fields=ACCOUNT_FIELDS, row_model=AccountSeedRow)


def test_empty_optional_manager_and_derived_is_manager(tmp_path: Path):
    _write_csv(
        tmp_path / "accounts.csv",
        "account_id,account_name,fiscal_year,budget_allocated,remaining_budget,currency\n"
        "ACC-001,Acme,2026,100,50,INR\n",
    )
    _write_csv(
        tmp_path / "projects.csv",
        "account_id,project_name,project_code,project_lead_id\n"
        "ACC-001,Capstone,CAPSTONE-001,EMP-002\n",
    )
    _write_csv(
        tmp_path / "employees.csv",
        "employee_id,employee_name,job_level,manager_id,project_code\n"
        "EMP-001,Rajesh Kumar,L5,,CAPSTONE-001\n"
        "EMP-002,Vikram Singh,L4,EMP-001,CAPSTONE-001\n"
        "EMP-007,Ananya Singh,L3,EMP-002,CAPSTONE-002\n",
    )
    tables = load_seed_tables(tmp_path)
    by_id = {row.employee_id: row for row in tables.employees.rows}
    assert "is_manager" not in (tmp_path / "employees.csv").read_text()
    assert by_id["EMP-001"].is_manager is True
    assert by_id["EMP-001"].manager_id is None
    assert by_id["EMP-002"].is_manager is True
    assert by_id["EMP-007"].is_manager is False
    assert by_id["EMP-007"].manager_id == "EMP-002"
    assert by_id["EMP-001"].job_level is JobLevel.L5


def test_derive_is_manager_from_manager_and_lead_ids():
    employees = (
        EmployeeSeedRow(
            employee_id="EMP-001",
            employee_name="Boss",
            job_level=JobLevel.L5,
            manager_id=None,
            project_code="P1",
        ),
        EmployeeSeedRow(
            employee_id="EMP-002",
            employee_name="Lead",
            job_level=JobLevel.L4,
            manager_id="EMP-001",
            project_code="P1",
        ),
        EmployeeSeedRow(
            employee_id="EMP-003",
            employee_name="IC",
            job_level=JobLevel.L3,
            manager_id="EMP-002",
            project_code="P1",
        ),
    )
    projects = (
        ProjectSeedRow(
            project_code="P1",
            project_name="Project",
            account_id="ACC-001",
            project_lead_id="EMP-002",
        ),
    )
    derived = {row.employee_id: row.is_manager for row in derive_is_manager(employees, projects)}
    assert derived == {"EMP-001": True, "EMP-002": True, "EMP-003": False}


def test_real_seed_csvs_map_expected_counts():
    data_dir = Path(__file__).resolve().parents[4] / "data" / "seed"
    tables = load_seed_tables(data_dir)
    assert len(tables.accounts.rows) == 5
    assert len(tables.projects.rows) == 10
    assert len(tables.employees.rows) == 61
    assert tables.accounts.ignored_columns == ("spent_amount", "account_hr_id")
    by_id = {row.employee_id: row for row in tables.employees.rows}
    assert by_id["EMP-001"].is_manager is True
    assert by_id["EMP-001"].manager_id is None
    assert by_id["EMP-007"].manager_id == "EMP-002"
    leads = {row.project_code: row.project_lead_id for row in tables.projects.rows}
    assert leads["CAPSTONE-001"] == "EMP-002"


def test_unknown_future_headers_are_ignored(tmp_path: Path):
    path = _write_csv(
        tmp_path / "accounts.csv",
        "account_id,account_name,fiscal_year,budget_allocated,remaining_budget,"
        "currency,brand_new_column\n"
        "ACC-001,Acme,2026,1,1,INR,xyz\n",
    )
    mapped = map_csv_file(path, fields=ACCOUNT_FIELDS, row_model=AccountSeedRow)
    assert "brand_new_column" in mapped.ignored_columns
