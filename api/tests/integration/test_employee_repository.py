"""Paging, filtering and sorting all happen in the database. These are the boundary cases."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.filters import EmployeeFilter, SortDirection, SortField, SortSpec
from app.domain.pagination import PageRequest
from app.infrastructure.repositories import SqlEmployeeRepository
from tests.conftest import add_employee


def repo(session: Session) -> SqlEmployeeRepository:
    return SqlEmployeeRepository(session)


def make_people(session: Session, count: int) -> None:
    for index in range(count):
        add_employee(
            session,
            full_name=f"Person {index:03d}",
            email=f"person{index:03d}@acme.test",
            salary_amount=f"{50000 + index}.00",
        )


def test_a_page_returns_only_its_slice_but_the_real_total(session: Session):
    make_people(session, 130)

    page = repo(session).list_employees(
        EmployeeFilter.build(), SortSpec(), PageRequest(page=2, page_size=50)
    )

    assert len(page.items) == 50
    assert page.total == 130
    assert page.total_pages == 3
    assert page.has_next is True


def test_consecutive_pages_do_not_overlap_or_skip(session: Session):
    make_people(session, 75)
    repository = repo(session)

    seen = []
    for number in (1, 2, 3):
        page = repository.list_employees(
            EmployeeFilter.build(), SortSpec(), PageRequest(page=number, page_size=25)
        )
        seen.extend(employee.id for employee in page.items)

    assert len(seen) == 75
    assert len(set(seen)) == 75


def test_the_last_page_is_short_and_says_there_is_no_next(session: Session):
    make_people(session, 55)

    page = repo(session).list_employees(
        EmployeeFilter.build(), SortSpec(), PageRequest(page=3, page_size=25)
    )

    assert len(page.items) == 5
    assert page.has_next is False


def test_a_page_past_the_end_is_empty_and_still_reports_the_total(session: Session):
    make_people(session, 10)

    page = repo(session).list_employees(
        EmployeeFilter.build(), SortSpec(), PageRequest(page=99, page_size=25)
    )

    assert page.items == []
    assert page.total == 10


def test_ties_are_broken_by_id_so_paging_is_repeatable(session: Session):
    # every row has the same name and the same pay, so only the tie-breaker decides the order
    for index in range(20):
        add_employee(session, full_name="Same Name", email=f"same{index}@acme.test")

    repository = repo(session)
    sort = SortSpec(SortField.NAME, SortDirection.ASC)
    first = repository.list_employees(EmployeeFilter.build(), sort, PageRequest(1, 10))
    second = repository.list_employees(EmployeeFilter.build(), sort, PageRequest(2, 10))

    ids = [employee.id for employee in first.items] + [employee.id for employee in second.items]
    assert ids == sorted(ids)
    assert len(set(ids)) == 20


def test_sorting_by_pay_compares_converted_salaries_not_raw_numbers(session: Session):
    add_employee(session, full_name="Rupee", salary_amount="200000.00", currency_code="INR")
    add_employee(session, full_name="Dollar", salary_amount="120000.00", currency_code="USD")
    add_employee(session, full_name="Euro", salary_amount="80000.00", currency_code="EUR")

    page = repo(session).list_employees(
        EmployeeFilter.build(),
        SortSpec(SortField.SALARY_USD, SortDirection.DESC),
        PageRequest(1, 10),
    )

    assert [employee.full_name for employee in page.items] == ["Euro", "Dollar", "Rupee"]


def test_sorting_by_the_native_amount_is_a_different_order(session: Session):
    add_employee(session, full_name="Rupee", salary_amount="200000.00", currency_code="INR")
    add_employee(session, full_name="Dollar", salary_amount="120000.00", currency_code="USD")

    page = repo(session).list_employees(
        EmployeeFilter.build(),
        SortSpec(SortField.SALARY_NATIVE, SortDirection.DESC),
        PageRequest(1, 10),
    )

    assert [employee.full_name for employee in page.items] == ["Rupee", "Dollar"]


def test_every_row_carries_both_the_paid_amount_and_the_converted_one(session: Session):
    add_employee(session, full_name="Euro", salary_amount="80000.00", currency_code="EUR")

    employee = repo(session).list_employees(
        EmployeeFilter.build(), SortSpec(), PageRequest(1, 10)
    ).items[0]

    assert employee.salary.amount == Decimal("80000.00")
    assert employee.salary.currency == "EUR"
    assert employee.salary_in_base.amount == Decimal("160000.00")
    assert employee.salary_in_base.currency == "USD"


def test_filters_within_one_dimension_are_an_or(session: Session):
    add_employee(session, full_name="A", country_code="US")
    add_employee(session, full_name="B", country_code="IN", currency_code="INR")
    add_employee(session, full_name="C", country_code="DE", currency_code="EUR")

    page = repo(session).list_employees(
        EmployeeFilter.build(countries=["US", "DE"]), SortSpec(), PageRequest(1, 10)
    )

    assert page.total == 2
    assert {employee.full_name for employee in page.items} == {"A", "C"}


def test_filters_across_dimensions_are_an_and(session: Session):
    add_employee(session, full_name="A", country_code="US", department="Sales")
    add_employee(session, full_name="B", country_code="US", department="Engineering")
    add_employee(session, full_name="C", country_code="IN", department="Sales",
                 currency_code="INR")

    page = repo(session).list_employees(
        EmployeeFilter.build(countries=["US"], departments=["Sales"]),
        SortSpec(),
        PageRequest(1, 10),
    )

    assert [employee.full_name for employee in page.items] == ["A"]


def test_search_matches_name_or_email_case_insensitively(session: Session):
    add_employee(session, full_name="Grace Hopper", email="grace@acme.test")
    add_employee(session, full_name="Alan Turing", email="hopper.fan@acme.test")
    add_employee(session, full_name="Ada Lovelace", email="ada@acme.test")

    page = repo(session).list_employees(
        EmployeeFilter.build(search="HOPPER"), SortSpec(), PageRequest(1, 10)
    )

    assert page.total == 2


def test_a_wildcard_in_the_search_term_is_treated_as_a_literal(session: Session):
    add_employee(session, full_name="Ada Lovelace", email="ada@acme.test")
    add_employee(session, full_name="100% Bonus", email="bonus@acme.test")

    page = repo(session).list_employees(
        EmployeeFilter.build(search="100%"), SortSpec(), PageRequest(1, 10)
    )

    assert page.total == 1
    assert page.items[0].full_name == "100% Bonus"


def test_hire_date_sorting_uses_the_date_not_the_string(session: Session):
    add_employee(session, full_name="Old", hire_date=date(2019, 3, 1))
    add_employee(session, full_name="New", hire_date=date(2026, 1, 9))

    page = repo(session).list_employees(
        EmployeeFilter.build(),
        SortSpec(SortField.HIRE_DATE, SortDirection.DESC),
        PageRequest(1, 10),
    )

    assert [employee.full_name for employee in page.items] == ["New", "Old"]


def test_a_row_carries_the_readable_country_name(session: Session):
    add_employee(session, country_code="IN", currency_code="INR")

    employee = repo(session).list_employees(
        EmployeeFilter.build(), SortSpec(), PageRequest(1, 10)
    ).items[0]

    assert employee.country_code == "IN"
    assert employee.country_name == "India"


def test_filter_options_come_from_the_data_and_are_sorted(session: Session):
    add_employee(session, full_name="A", country_code="US", department="Sales", role="Rep")
    add_employee(session, full_name="B", country_code="IN", department="Engineering",
                 role="Engineer", currency_code="INR")
    add_employee(session, full_name="C", country_code="US", department="Sales", role="Rep")

    options = repo(session).filter_options()

    assert options.countries == [("IN", "India"), ("US", "United States")]
    assert options.departments == ["Engineering", "Sales"]
    assert options.roles == ["Engineer", "Rep"]
