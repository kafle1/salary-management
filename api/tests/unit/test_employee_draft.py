from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.employee_draft import EmployeeDraft, InvalidEmployee
from app.domain.money import Money

TODAY = date(2026, 9, 13)


def build(**overrides):
    fields = {
        "full_name": "Ada Lovelace",
        "email": "ada@acme.example",
        "country_code": "DE",
        "department": "Engineering",
        "role": "Engineer",
        "hire_date": "2024-01-15",
        "salary_amount": "85000",
        "today": TODAY,
    }
    fields.update(overrides)
    return EmployeeDraft.build(**fields)


def errors_for(**overrides) -> dict[str, str]:
    with pytest.raises(InvalidEmployee) as caught:
        build(**overrides)
    return caught.value.errors


def test_a_clean_draft_is_tidied_and_paid_in_its_countrys_currency():
    draft = build(
        full_name="  Ada   Lovelace ",
        email=" Ada@ACME.example ",
        country_code=" de",
        department=" Engineering  ",
    )

    assert draft.full_name == "Ada Lovelace"
    assert draft.email == "ada@acme.example"
    assert draft.country_code == "DE"
    assert draft.department == "Engineering"
    assert draft.hire_date == date(2024, 1, 15)
    assert draft.salary == Money(Decimal("85000.00"), "EUR")


def test_every_problem_comes_back_at_once_so_the_form_can_show_them_together():
    errors = errors_for(
        full_name=" ",
        email=None,
        country_code="",
        department="",
        role="",
        hire_date="",
        salary_amount="",
    )

    assert set(errors) == {
        "full_name",
        "email",
        "country_code",
        "department",
        "role",
        "hire_date",
        "salary_amount",
    }


@pytest.mark.parametrize("email", ["ada", "ada@", "@acme.example", "ada@acme", "a da@acme.example"])
def test_an_email_has_to_look_like_one(email: str):
    assert "email" in errors_for(email=email)


def test_a_country_nobody_is_paid_in_is_refused():
    assert "country_code" in errors_for(country_code="FR")


@pytest.mark.parametrize(
    "amount",
    ["0", "-5", "abc", "NaN", "Infinity", "100.005", "1000000000000.00"],
)
def test_salary_has_to_be_a_positive_amount_the_column_can_hold(amount: str):
    assert "salary_amount" in errors_for(salary_amount=amount)


def test_salary_typed_with_thousands_separators_is_accepted():
    assert build(salary_amount="1,250,000.50").salary.amount == Decimal("1250000.50")


def test_salary_sent_as_a_json_number_is_accepted():
    assert build(salary_amount=85000.5).salary.amount == Decimal("85000.50")


def test_a_hire_date_in_the_future_is_refused():
    assert "hire_date" in errors_for(hire_date="2026-09-14")


def test_someone_hired_today_is_fine():
    assert build(hire_date="2026-09-13").hire_date == TODAY


def test_a_date_that_is_not_a_date_is_refused():
    assert "hire_date" in errors_for(hire_date="15/01/2024")


def test_text_longer_than_its_column_is_refused_rather_than_truncated():
    errors = errors_for(full_name="x" * 121, department="d" * 61, role="r" * 81)

    assert set(errors) == {"full_name", "department", "role"}


def test_a_blank_reason_is_no_reason():
    assert build(salary_note="   ").salary_note is None


def test_a_reason_is_kept_and_capped():
    assert build(salary_note=" annual review ").salary_note == "annual review"
    assert "salary_note" in errors_for(salary_note="x" * 201)
