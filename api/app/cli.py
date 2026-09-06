"""Admin commands. Schema creation lives here rather than in application startup, so nothing
creates tables as a side effect of someone importing the app."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError

from app.infrastructure.db import create_schema, get_engine, session_scope
from app.infrastructure.models import Base, Employee
from app.infrastructure.seed import DEFAULT_COUNT, DEFAULT_SEED, seed_all


def _wait_for_database(attempts: int = 30, delay: float = 1.0) -> None:
    """Compose starts the database and this in the same breath. Retry rather than crash-loop."""
    engine = get_engine()
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError:
            if attempt == attempts:
                raise
            time.sleep(delay)


def _seed(count: int, seed: int) -> int:
    with session_scope() as session:
        seed_all(session, count=count, seed=seed)
    # count what actually landed, not what we meant to write
    with session_scope() as session:
        return int(session.execute(select(func.count()).select_from(Employee)).scalar_one())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="salary-admin")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("create-schema", help="create the tables if they are missing")
    commands.add_parser("drop-schema", help="drop every table")

    seed_command = commands.add_parser("seed", help="replace all data with a deterministic set")
    seed_command.add_argument("--count", type=int, default=DEFAULT_COUNT)
    seed_command.add_argument("--seed", type=int, default=DEFAULT_SEED)

    reset_command = commands.add_parser("reset", help="create the schema then seed it")
    reset_command.add_argument("--count", type=int, default=DEFAULT_COUNT)
    reset_command.add_argument("--seed", type=int, default=DEFAULT_SEED)

    args = parser.parse_args(argv)
    _wait_for_database()

    if args.command == "create-schema":
        create_schema(get_engine())
        print("schema ready")
        return 0

    if args.command == "drop-schema":
        Base.metadata.drop_all(get_engine())
        print("schema dropped")
        return 0

    if args.command == "reset":
        create_schema(get_engine())

    total = _seed(args.count, args.seed)
    print(f"seeded {total} employees with seed {args.seed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
