"""An employee as HR typed it, checked before it goes anywhere near a table.

The rules live here and not in the request schema, so every caller gets the same answer and the
form can show every problem at once instead of one per submit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from app.domain.countries import BY_CODE
from app.domain.money import CENTS, Money

NAME_MAX = 120
EMAIL_MAX = 255
DEPARTMENT_MAX = 60
ROLE_MAX = 80
NOTE_MAX = 200
# Numeric(14, 2) holds twelve digits before the point
SALARY_MAX = Decimal("999999999999.99")

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

Errors = dict[str, str]


class InvalidEmployee(ValueError):
    def __init__(self, errors: Errors) -> None:
        super().__init__("; ".join(f"{field}: {message}" for field, message in errors.items()))
        self.errors = errors


@dataclass(frozen=True)
class EmployeeDraft:
    full_name: str
    email: str
    country_code: str
    department: str
    role: str
    hire_date: date
    # paid in the country's currency, which is also what guarantees an exchange rate exists
    salary: Money
    salary_note: str | None = None

    @classmethod
    def build(
        cls,
        *,
        full_name: str | None,
        email: str | None,
        country_code: str | None,
        department: str | None,
        role: str | None,
        hire_date: str | date | None,
        salary_amount: str | int | float | Decimal | None,
        salary_note: str | None = None,
        today: date | None = None,
    ) -> EmployeeDraft:
        errors: Errors = {}
        name = _text(full_name, "full_name", NAME_MAX, errors)
        clean_email = _email(email, errors)
        country = _country(country_code, errors)
        clean_department = _text(department, "department", DEPARTMENT_MAX, errors)
        clean_role = _text(role, "role", ROLE_MAX, errors)
        hired = _hire_date(hire_date, today or date.today(), errors)
        amount = _amount(salary_amount, errors)
        note = _text(salary_note, "salary_note", NOTE_MAX, errors, required=False)
        if errors:
            raise InvalidEmployee(errors)
        return cls(
            full_name=name,
            email=clean_email,
            country_code=country,
            department=clean_department,
            role=clean_role,
            hire_date=hired,
            salary=Money(amount, BY_CODE[country].currency),
            salary_note=note or None,
        )


def _text(value: str | None, field: str, limit: int, errors: Errors, required: bool = True) -> str:
    # collapsing inner spaces too, or "Sales" and "Sales " become two departments on the dashboard
    text = " ".join((value or "").split())
    if required and not text:
        errors[field] = "Required."
    elif len(text) > limit:
        errors[field] = f"Keep it to {limit} characters or fewer."
    return text


def _email(value: str | None, errors: Errors) -> str:
    text = (value or "").strip().lower()
    if not text:
        errors["email"] = "Required."
    elif len(text) > EMAIL_MAX or not _EMAIL.match(text):
        errors["email"] = "That doesn't look like an email address."
    return text


def _country(value: str | None, errors: Errors) -> str:
    code = (value or "").strip().upper()
    if not code:
        errors["country_code"] = "Required."
    elif code not in BY_CODE:
        errors["country_code"] = "Pick one of the countries the company pays people in."
    return code


def _hire_date(value: str | date | None, today: date, errors: Errors) -> date:
    if isinstance(value, date):
        parsed = value
    elif not (value or "").strip():
        errors["hire_date"] = "Required."
        return today
    else:
        try:
            parsed = date.fromisoformat(value.strip())
        except ValueError:
            errors["hire_date"] = "Use a date like 2024-01-15."
            return today
    if parsed > today:
        # a future starter is not on payroll yet, and counting them would skew every total
        errors["hire_date"] = "A hire date can't be in the future."
    return parsed


def _amount(value: str | int | float | Decimal | None, errors: Errors) -> Decimal:
    text = str(value if value is not None else "").strip().replace(",", "")
    if not text:
        errors["salary_amount"] = "Required."
        return Decimal("0")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        errors["salary_amount"] = "Enter a number, like 85000."
        return Decimal("0")
    if not amount.is_finite():
        errors["salary_amount"] = "Enter a number, like 85000."
    elif amount <= 0:
        errors["salary_amount"] = "Salary has to be above zero."
    elif amount > SALARY_MAX:
        errors["salary_amount"] = "That's more than the salary column can hold."
    elif amount != amount.quantize(CENTS):
        errors["salary_amount"] = "Use at most two decimal places."
    return amount
