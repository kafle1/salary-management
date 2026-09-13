"""Writes run against the real schema, so the unique email and the history are the database's."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.employee import EmailAlreadyUsed, EmployeeNotFound
from app.domain.employee_draft import EmployeeDraft
from app.domain.money import Money
from app.infrastructure.models import SalaryChange as SalaryChangeRow
from app.infrastructure.repositories import SqlEmployeeRepository
from tests.conftest import add_employee


def draft(**overrides) -> EmployeeDraft:
    fields = {
        "full_name": "Grace Hopper",
        "email": "grace@acme.test",
        "country_code": "DE",
        "department": "Engineering",
        "role": "Engineer",
        "hire_date": "2024-03-01",
        "salary_amount": "60000.00",
    }
    fields.update(overrides)
    return EmployeeDraft.build(**fields)


def test_a_new_employee_comes_back_with_their_pay_already_converted(session: Session):
    created = SqlEmployeeRepository(session).create(draft())

    assert created.id is not None
    assert created.country_name == "Germany"
    assert created.salary == Money(Decimal("60000.00"), "EUR")
    assert created.salary_in_base == Money(Decimal("120000.00"), "USD")


def test_a_new_employee_starts_with_one_history_row_and_no_previous_salary(session: Session):
    repository = SqlEmployeeRepository(session)

    created = repository.create(draft(salary_note="Offer letter"))

    [start] = repository.history(created.id)
    assert start.previous is None
    assert start.new == Money(Decimal("60000.00"), "EUR")
    assert start.note == "Offer letter"


def test_a_duplicate_email_that_slips_past_the_service_is_still_refused(session: Session):
    add_employee(session, email="grace@acme.test")
    session.commit()

    with pytest.raises(EmailAlreadyUsed):
        SqlEmployeeRepository(session).create(draft(email="grace@acme.test"))

    # the failed insert rolled back cleanly, so the session is still usable
    assert SqlEmployeeRepository(session).email_taken("grace@acme.test") is True


def test_email_taken_can_ignore_the_person_being_edited(session: Session):
    ada = add_employee(session, email="ada@acme.test")
    session.commit()
    repository = SqlEmployeeRepository(session)

    assert repository.email_taken("ada@acme.test") is True
    assert repository.email_taken("ada@acme.test", exclude_id=ada.id) is False
    assert repository.email_taken("nobody@acme.test") is False


def test_looking_up_a_missing_id_is_none_not_an_error(session: Session):
    assert SqlEmployeeRepository(session).get(404) is None


def test_a_raise_rewrites_the_employee_and_adds_a_history_row_on_top(session: Session):
    repository = SqlEmployeeRepository(session)
    created = repository.create(draft())

    updated = repository.update(
        created.id,
        draft(role="Senior Engineer", salary_amount="66000", salary_note="Promotion"),
        record_salary_change=True,
    )

    assert updated.role == "Senior Engineer"
    assert updated.salary_in_base == Money(Decimal("132000.00"), "USD")
    latest, start = repository.history(created.id)
    assert latest.previous == Money(Decimal("60000.00"), "EUR")
    assert latest.new == Money(Decimal("66000.00"), "EUR")
    assert latest.note == "Promotion"
    assert start.previous is None


def test_an_edit_that_is_not_a_pay_change_leaves_the_history_alone(session: Session):
    repository = SqlEmployeeRepository(session)
    created = repository.create(draft())

    repository.update(created.id, draft(full_name="Grace B. Hopper"), record_salary_change=False)

    assert repository.get(created.id).full_name == "Grace B. Hopper"
    assert len(repository.history(created.id)) == 1


def test_moving_to_a_colleagues_email_is_refused_and_nothing_changes(session: Session):
    add_employee(session, email="ada@acme.test")
    session.commit()
    repository = SqlEmployeeRepository(session)
    created = repository.create(draft())

    with pytest.raises(EmailAlreadyUsed):
        repository.update(
            created.id, draft(email="ada@acme.test", role="CTO"), record_salary_change=False
        )

    assert repository.get(created.id).role == "Engineer"


def test_updating_a_missing_id_is_a_not_found(session: Session):
    with pytest.raises(EmployeeNotFound):
        SqlEmployeeRepository(session).update(404, draft(), record_salary_change=False)


def test_deleting_someone_takes_their_history_with_them(session: Session):
    repository = SqlEmployeeRepository(session)
    created = repository.create(draft())
    repository.update(created.id, draft(salary_amount="70000"), record_salary_change=True)

    assert repository.delete(created.id) is True

    assert repository.get(created.id) is None
    leftover = select(func.count()).select_from(SalaryChangeRow)
    assert session.execute(leftover).scalar_one() == 0


def test_deleting_twice_reports_the_second_one_found_nothing(session: Session):
    repository = SqlEmployeeRepository(session)
    created = repository.create(draft())
    repository.delete(created.id)

    assert repository.delete(created.id) is False


def test_history_rows_are_dated_the_day_they_were_written(session: Session):
    repository = SqlEmployeeRepository(session)

    created = repository.create(draft())

    assert repository.history(created.id)[0].changed_on == date.today()
