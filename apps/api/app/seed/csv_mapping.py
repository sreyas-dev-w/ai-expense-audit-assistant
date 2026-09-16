"""Schema-tolerant CSV mapping for the one-time database seed.

CSV headers are matched after normalization so ``account_id``, ``Account ID``,
and ``accountid`` all bind to the same field. Unknown columns are ignored
(and reported). Required mapped fields that are missing from the header row
fail with a clear column list.
"""
from __future__ import annotations

import csv
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.models.enums import Currency, JobLevel
from app.schemas.seed import AccountSeedRow, EmployeeSeedRow, ProjectSeedRow

logger = logging.getLogger(__name__)

_NON_ALNUM = re.compile(r"[^a-z0-9]")

ACCOUNTS_FILENAME = "accounts.csv"
PROJECTS_FILENAME = "projects.csv"
EMPLOYEES_FILENAME = "employees.csv"


class SeedMappingError(ValueError):
    """CSV headers or values could not be mapped onto the persistence models."""


@dataclass(frozen=True)
class FieldSpec:
    name: str
    aliases: tuple[str, ...] = ()
    required: bool = True
    default: Any = None
    coerce: Callable[[str], Any] | None = None


@dataclass(frozen=True)
class MappedCsv[T]:
    rows: tuple[T, ...]
    ignored_columns: tuple[str, ...]
    filename: str


@dataclass(frozen=True)
class SeedTables:
    accounts: MappedCsv[AccountSeedRow]
    projects: MappedCsv[ProjectSeedRow]
    employees: MappedCsv[EmployeeSeedRow]


TModel = TypeVar("TModel", bound=BaseModel)


def normalize_header(header: str) -> str:
    """Collapse a header to lowercase alphanumeric characters only."""
    return _NON_ALNUM.sub("", header.strip().lower())


def _alias_keys(spec: FieldSpec) -> set[str]:
    return {normalize_header(name) for name in (spec.name, *spec.aliases)}


def coerce_required_str(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise SeedMappingError("value is empty")
    return value


def coerce_optional_str(raw: str) -> str | None:
    value = raw.strip()
    return value or None


def coerce_int(raw: str) -> int:
    value = raw.strip()
    if not value:
        raise SeedMappingError("value is empty")
    try:
        return int(value)
    except ValueError as exc:
        raise SeedMappingError(f"not an integer: {raw!r}") from exc


def coerce_decimal(raw: str) -> Decimal:
    value = raw.strip()
    if not value:
        raise SeedMappingError("value is empty")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise SeedMappingError(f"not a decimal: {raw!r}") from exc


def coerce_enum(enum_cls: type[Enum]) -> Callable[[str], Enum]:
    members_by_key = {}
    for member in enum_cls:
        members_by_key[normalize_header(member.name)] = member
        members_by_key[normalize_header(str(member.value))] = member

    labels = ", ".join(member.name for member in enum_cls)

    def _coerce(raw: str) -> Enum:
        value = raw.strip()
        if not value:
            raise SeedMappingError("value is empty")
        member = members_by_key.get(normalize_header(value))
        if member is None:
            raise SeedMappingError(f"invalid value {raw!r}; expected one of {labels}")
        return member

    return _coerce


ACCOUNT_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(name="account_id", aliases=("Account ID", "accountid"), coerce=coerce_required_str),
    FieldSpec(
        name="account_name",
        aliases=("Account Name", "accountname"),
        coerce=coerce_required_str,
    ),
    FieldSpec(
        name="fiscal_year",
        aliases=("Fiscal Year", "fiscalyear", "year"),
        coerce=coerce_int,
    ),
    FieldSpec(
        name="budget_allocated",
        aliases=("Budget Allocated", "budgetallocated"),
        coerce=coerce_decimal,
    ),
    FieldSpec(
        name="remaining_budget",
        aliases=("Remaining Budget", "remainingbudget"),
        coerce=coerce_decimal,
    ),
    FieldSpec(
        name="currency",
        aliases=("Currency",),
        coerce=coerce_enum(Currency),
    ),
)

PROJECT_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        name="project_code",
        aliases=("Project Code", "projectcode"),
        coerce=coerce_required_str,
    ),
    FieldSpec(
        name="project_name",
        aliases=("Project Name", "projectname"),
        coerce=coerce_required_str,
    ),
    FieldSpec(
        name="account_id",
        aliases=("Account ID", "accountid"),
        coerce=coerce_required_str,
    ),
    FieldSpec(
        name="project_lead_id",
        aliases=("Project Lead ID", "projectleadid", "lead_id"),
        required=False,
        coerce=coerce_optional_str,
    ),
)

EMPLOYEE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        name="employee_id",
        aliases=("Employee ID", "employeeid"),
        coerce=coerce_required_str,
    ),
    FieldSpec(
        name="employee_name",
        aliases=("Employee Name", "employeename"),
        coerce=coerce_required_str,
    ),
    FieldSpec(
        name="job_level",
        aliases=("Job Level", "joblevel", "level"),
        coerce=coerce_enum(JobLevel),
    ),
    FieldSpec(
        name="manager_id",
        aliases=("Manager ID", "managerid"),
        required=False,
        coerce=coerce_optional_str,
    ),
    FieldSpec(
        name="project_code",
        aliases=("Project Code", "projectcode"),
        required=False,
        coerce=coerce_optional_str,
    ),
)


def _bind_headers(
    headers: Sequence[str | None],
    fields: Sequence[FieldSpec],
    *,
    filename: str,
) -> tuple[dict[str, str], tuple[str, ...]]:
    present = [header for header in headers if header is not None and header.strip()]
    unused = list(present)
    bound: dict[str, str] = {}
    duplicates: list[str] = []

    for spec in fields:
        keys = _alias_keys(spec)
        matches = [header for header in present if normalize_header(header) in keys]
        if not matches:
            continue
        if len(matches) > 1:
            duplicates.append(f"{spec.name} ({', '.join(matches)})")
            continue
        header = matches[0]
        bound[spec.name] = header
        if header in unused:
            unused.remove(header)

    if duplicates:
        raise SeedMappingError(
            f"{filename}: duplicate columns for the same field: {'; '.join(duplicates)}"
        )

    missing = [spec.name for spec in fields if spec.required and spec.name not in bound]
    if missing:
        raise SeedMappingError(
            f"{filename}: missing required columns: {', '.join(missing)}"
        )

    ignored = tuple(unused)
    if ignored:
        logger.warning("Ignoring extra CSV columns in %s: %s", filename, ", ".join(ignored))
    return bound, ignored


def map_csv_file(
    path: Path,
    *,
    fields: Sequence[FieldSpec],
    row_model: type[TModel],
) -> MappedCsv[TModel]:
    filename = path.name
    if not path.is_file():
        raise SeedMappingError(f"seed file not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SeedMappingError(f"{filename}: CSV has no header row")
        bound, ignored = _bind_headers(reader.fieldnames, fields, filename=filename)
        rows: list[TModel] = []
        for raw_row in reader:
            if not any((value or "").strip() for value in raw_row.values()):
                continue
            mapped: dict[str, Any] = {}
            for spec in fields:
                header = bound.get(spec.name)
                if header is None:
                    mapped[spec.name] = spec.default
                    continue
                raw = raw_row.get(header) or ""
                coerce = spec.coerce
                try:
                    mapped[spec.name] = coerce(raw) if coerce is not None else raw.strip()
                except SeedMappingError as exc:
                    raise SeedMappingError(
                        f"{filename} row {reader.line_num}: field {spec.name}: {exc}"
                    ) from exc
            try:
                rows.append(row_model.model_validate(mapped))
            except ValidationError as exc:
                raise SeedMappingError(
                    f"{filename} row {reader.line_num}: {exc}"
                ) from exc

    return MappedCsv(rows=tuple(rows), ignored_columns=ignored, filename=filename)


def derive_is_manager(
    employees: Sequence[EmployeeSeedRow],
    projects: Sequence[ProjectSeedRow],
) -> tuple[EmployeeSeedRow, ...]:
    """Mark employees who appear as a manager or project lead."""
    manager_ids = {row.manager_id for row in employees if row.manager_id}
    lead_ids = {row.project_lead_id for row in projects if row.project_lead_id}
    flagged = manager_ids | lead_ids
    return tuple(
        row.model_copy(update={"is_manager": row.employee_id in flagged})
        for row in employees
    )


def load_seed_tables(data_dir: Path) -> SeedTables:
    accounts = map_csv_file(
        data_dir / ACCOUNTS_FILENAME,
        fields=ACCOUNT_FIELDS,
        row_model=AccountSeedRow,
    )
    projects = map_csv_file(
        data_dir / PROJECTS_FILENAME,
        fields=PROJECT_FIELDS,
        row_model=ProjectSeedRow,
    )
    employees = map_csv_file(
        data_dir / EMPLOYEES_FILENAME,
        fields=EMPLOYEE_FIELDS,
        row_model=EmployeeSeedRow,
    )
    derived = derive_is_manager(employees.rows, projects.rows)
    employees = MappedCsv(
        rows=derived,
        ignored_columns=employees.ignored_columns,
        filename=employees.filename,
    )
    return SeedTables(accounts=accounts, projects=projects, employees=employees)
