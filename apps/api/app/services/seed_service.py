"""One-time CSV seed orchestration (accounts, projects, employees)."""
from pathlib import Path

from app.db.session import async_session_factory
from app.repositories.seed_repository import SeedRepository
from app.schemas.seed import (
    IgnoredCsvColumns,
    SeedLoadReport,
    SeedTableCounts,
)
from app.seed.csv_mapping import SeedMappingError, load_seed_tables


class SeedAlreadyPopulatedError(RuntimeError):
    """Default load refuses to run when target tables already have rows."""

    def __init__(self, counts: SeedTableCounts) -> None:
        self.counts = counts
        super().__init__(
            "Refusing to seed: accounts, projects, or employees already have "
            f"rows (accounts={counts.accounts}, projects={counts.projects}, "
            f"employees={counts.employees}). Re-run with --force to reload."
        )


class SeedService:
    def __init__(self, session_factory=async_session_factory) -> None:
        self._session_factory = session_factory

    async def load_from_csv_dir(
        self,
        data_dir: Path,
        *,
        force: bool = False,
        dry_run: bool = False,
    ) -> SeedLoadReport:
        tables = load_seed_tables(data_dir)
        ignored = [
            IgnoredCsvColumns(file=mapped.filename, columns=list(mapped.ignored_columns))
            for mapped in (tables.accounts, tables.projects, tables.employees)
            if mapped.ignored_columns
        ]
        would_insert = SeedTableCounts(
            accounts=len(tables.accounts.rows),
            projects=len(tables.projects.rows),
            employees=len(tables.employees.rows),
        )
        is_manager_count = sum(1 for row in tables.employees.rows if row.is_manager)
        empty = SeedTableCounts(accounts=0, projects=0, employees=0)

        if dry_run:
            return SeedLoadReport(
                dry_run=True,
                forced=force,
                inserted=empty,
                skipped=would_insert,
                ignored_columns=ignored,
                is_manager_count=is_manager_count,
            )

        async with self._session_factory() as session:
            repository = SeedRepository(session)
            try:
                counts = await repository.count_rows()
                if not force and counts.any_populated:
                    raise SeedAlreadyPopulatedError(counts)
                if force:
                    await repository.delete_seed_graph()
                await repository.insert_accounts(tables.accounts.rows)
                await repository.insert_projects_without_leads(tables.projects.rows)
                await repository.insert_employees_without_managers(
                    tables.employees.rows
                )
                await repository.update_employee_managers(tables.employees.rows)
                await repository.update_project_leads(tables.projects.rows)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

        return SeedLoadReport(
            dry_run=False,
            forced=force,
            inserted=would_insert,
            skipped=empty,
            ignored_columns=ignored,
            is_manager_count=is_manager_count,
        )


__all__ = [
    "SeedAlreadyPopulatedError",
    "SeedMappingError",
    "SeedService",
]
