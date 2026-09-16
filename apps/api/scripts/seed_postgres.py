"""One-time CLI loader: data/seed CSV files → Postgres.

Usage (from apps/api, after ``alembic upgrade head``):

    python scripts/seed_postgres.py
    python scripts/seed_postgres.py --dry-run
    python scripts/seed_postgres.py --force
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.schemas.seed import SeedLoadReport  # noqa: E402
from app.services.seed_service import (  # noqa: E402
    SeedAlreadyPopulatedError,
    SeedMappingError,
    SeedService,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "seed"
FORCE_WARNING = (
    "WARNING: --force deletes claims, agent_response, employees, projects, "
    "and accounts before reloading. Dev-only."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load accounts, projects, and employees from CSV into Postgres."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing accounts.csv, projects.csv, and employees.csv "
        f"(default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing seed-table rows (FK-safe) and reload.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate CSVs, print counts, write nothing.",
    )
    return parser.parse_args(argv)


def _print_report(report: SeedLoadReport) -> None:
    verb = "would insert" if report.dry_run else "inserted"
    skipped_label = "parsed" if report.dry_run else "skipped"
    counts = report.skipped if report.dry_run else report.inserted
    if report.dry_run:
        print("Dry run - no database writes.")
    elif report.forced:
        print("Forced reload complete.")
    else:
        print("Seed complete.")
    print(f"  accounts:  {counts.accounts} {verb}")
    print(f"  projects:  {counts.projects} {verb}")
    print(f"  employees: {counts.employees} {verb}")
    print(f"  is_manager true: {report.is_manager_count}")
    if not report.dry_run and report.skipped.any_populated:
        print(
            f"  {skipped_label}: accounts={report.skipped.accounts}, "
            f"projects={report.skipped.projects}, employees={report.skipped.employees}"
        )
    if report.ignored_columns:
        print("Ignored columns:")
        for ignored in report.ignored_columns:
            print(f"  {ignored.file}: {', '.join(ignored.columns)}")


async def _run(args: argparse.Namespace) -> int:
    if args.force and not args.dry_run:
        print(FORCE_WARNING, file=sys.stderr)
    try:
        report = await SeedService().load_from_csv_dir(
            args.data_dir,
            force=args.force,
            dry_run=args.dry_run,
        )
    except SeedAlreadyPopulatedError as exc:
        print(exc, file=sys.stderr)
        return 1
    except SeedMappingError as exc:
        print(f"Seed mapping failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    _print_report(report)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    args = parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
