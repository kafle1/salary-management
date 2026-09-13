"""What the rest of the system sees when it asks for an employee.

Deliberately not the SQLAlchemy model. Repositories map rows into this, so a lazy load can never
fire halfway through serialising a response and the API layer has nothing to say about SQL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.money import Money


class EmployeeNotFound(LookupError):
    def __init__(self, employee_id: int) -> None:
        super().__init__(f"No employee with id {employee_id}.")


class EmailAlreadyUsed(ValueError):
    def __init__(self, email: str) -> None:
        super().__init__(f"{email} already belongs to someone else.")


@dataclass(frozen=True)
class Employee:
    id: int
    full_name: str
    email: str
    country_code: str
    country_name: str
    department: str
    role: str
    hire_date: date
    salary: Money
    salary_in_base: Money


@dataclass(frozen=True)
class SalaryChange:
    """One move in someone's pay. `previous` is None for the salary they were added on."""

    changed_at: datetime
    previous: Money | None
    new: Money
    note: str | None


@dataclass(frozen=True)
class EmployeeDetail:
    employee: Employee
    history: list[SalaryChange]


@dataclass(frozen=True)
class FilterOptions:
    """Every value the UI is allowed to filter on, read from the data rather than hardcoded."""

    countries: list[tuple[str, str]]
    departments: list[str]
    roles: list[str]
