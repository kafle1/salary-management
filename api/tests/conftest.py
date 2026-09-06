"""Test fixtures.

The suite runs on SQLite in-memory. It costs one real constraint, no Postgres-only SQL anywhere
in a query path, and it buys a suite that finishes in seconds with nothing to install. Foreign
keys are switched on so the fixtures fail the same way Postgres would.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.infrastructure.models import Base, Employee, ExchangeRate

# deliberately round numbers, not market rates. a test you can check in your head is worth more
# than a realistic one you cannot.
TEST_RATES: dict[str, Decimal] = {
    "USD": Decimal("1.00000000"),
    "EUR": Decimal("2.00000000"),
    "INR": Decimal("0.50000000"),
}


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        for code, rate in TEST_RATES.items():
            session.add(ExchangeRate(currency_code=code, usd_per_unit=rate, as_of=date(2026, 8, 1)))
        session.commit()
        yield session


def add_employee(
    session: Session,
    *,
    full_name: str = "Ada Lovelace",
    email: str | None = None,
    country_code: str = "US",
    department: str = "Engineering",
    role: str = "Engineer",
    hire_date: date = date(2024, 1, 15),
    salary_amount: str = "100000.00",
    currency_code: str = "USD",
) -> Employee:
    employee = Employee(
        full_name=full_name,
        email=email or f"{full_name.lower().replace(' ', '.')}@acme.test",
        country_code=country_code,
        department=department,
        role=role,
        hire_date=hire_date,
        salary_amount=Decimal(salary_amount),
        currency_code=currency_code,
    )
    session.add(employee)
    session.flush()
    return employee
