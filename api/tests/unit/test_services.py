"""Service tests with hand-written fakes and no database.

This is the whole point of the ports: the rules about how a request turns into a query are worth
testing, and none of them need SQL to be true.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.application.queries import DashboardQuery, EmployeeInput, EmployeeQuery
from app.application.services import DashboardService, EmployeeService
from app.domain.employee import EmailAlreadyUsed, Employee, EmployeeNotFound, FilterOptions
from app.domain.employee_draft import EmployeeDraft, InvalidEmployee
from app.domain.filters import (
    EmployeeFilter,
    GroupBy,
    SortDirection,
    SortField,
    UnknownGroupBy,
    UnknownSortField,
)
from app.domain.money import Money
from app.domain.pagination import Page, PageRequest
from app.domain.summary import GroupStats, SalaryStats


class FakeEmployeeReader:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def list_employees(self, filters, sort, page):
        self.calls.append((filters, sort, page))
        return Page(items=[], total=0, request=page)

    def filter_options(self):
        return FilterOptions(countries=[("US", "United States")], departments=["Sales"], roles=[])


class FakeAnalytics:
    def __init__(self) -> None:
        self.overall_calls: list[EmployeeFilter] = []
        self.group_calls: list[tuple[EmployeeFilter, GroupBy]] = []

    def overall(self, filters):
        self.overall_calls.append(filters)
        return SalaryStats(
            headcount=3,
            total_payroll=Decimal("300000.00"),
            average_salary=Decimal("100000.00"),
            median_salary=Decimal("90000.00"),
        )

    def by_group(self, filters, group_by):
        self.group_calls.append((filters, group_by))
        return [GroupStats(key="US", label="United States", stats=SalaryStats(headcount=3))]


def test_raw_request_values_are_normalised_before_they_reach_the_repository():
    reader = FakeEmployeeReader()

    EmployeeService(reader).list(
        EmployeeQuery(
            countries=["us", " in ", ""],
            departments=["Sales", "Sales"],
            search="  ada ",
            sort_by="SALARY_USD",
            sort_direction="desc",
            page=3,
            page_size=50,
        )
    )

    filters, sort, page = reader.calls[0]
    assert filters.countries == ("US", "IN")
    assert filters.departments == ("Sales",)
    assert filters.search == "ada"
    assert sort.field is SortField.SALARY_USD
    assert sort.direction is SortDirection.DESC
    assert page == PageRequest(page=3, page_size=50)


def test_an_untouched_query_uses_the_defaults():
    reader = FakeEmployeeReader()

    EmployeeService(reader).list(EmployeeQuery())

    filters, sort, page = reader.calls[0]
    assert filters.is_empty is True
    assert sort.field is SortField.NAME
    assert page == PageRequest(page=1, page_size=25)


def test_a_bad_sort_field_is_rejected_before_any_query_runs():
    reader = FakeEmployeeReader()

    with pytest.raises(UnknownSortField):
        EmployeeService(reader).list(EmployeeQuery(sort_by="salary; drop table employees"))

    assert reader.calls == []


def test_an_oversized_page_is_rejected_before_any_query_runs():
    reader = FakeEmployeeReader()

    with pytest.raises(ValueError):
        EmployeeService(reader).list(EmployeeQuery(page_size=100_000))

    assert reader.calls == []


def test_filter_options_are_passed_straight_through():
    options = EmployeeService(FakeEmployeeReader()).filter_options()

    assert options.countries == [("US", "United States")]


def test_the_cards_and_the_breakdown_see_the_same_filter():
    analytics = FakeAnalytics()

    summary = DashboardService(analytics).summary(
        DashboardQuery(countries=["de"], group_by="department")
    )

    assert analytics.overall_calls[0] == analytics.group_calls[0][0]
    assert analytics.group_calls[0][1] is GroupBy.DEPARTMENT
    assert summary.group_by is GroupBy.DEPARTMENT
    assert summary.overall.headcount == 3
    assert summary.base_currency == "USD"
    assert [group.key for group in summary.groups] == ["US"]


def test_grouping_defaults_to_country():
    analytics = FakeAnalytics()

    assert DashboardService(analytics).summary(DashboardQuery()).group_by is GroupBy.COUNTRY


def test_an_unknown_grouping_is_refused():
    with pytest.raises(UnknownGroupBy):
        DashboardService(FakeAnalytics()).summary(DashboardQuery(group_by="astrology"))


def employee(employee_id: int = 1, email: str = "ada@acme.example", amount: str = "85000.00"):
    return Employee(
        id=employee_id,
        full_name="Ada Lovelace",
        email=email,
        country_code="DE",
        country_name="Germany",
        department="Engineering",
        role="Engineer",
        hire_date=date(2024, 1, 15),
        salary=Money(Decimal(amount), "EUR"),
        salary_in_base=Money(Decimal(amount), "USD"),
    )


class FakeEmployeeStore(FakeEmployeeReader):
    def __init__(self, *existing: Employee) -> None:
        super().__init__()
        self.people = {person.id: person for person in existing}
        self.created: list[EmployeeDraft] = []
        self.updated: list[tuple[int, EmployeeDraft, bool]] = []
        self.deleted: list[int] = []

    def get(self, employee_id):
        return self.people.get(employee_id)

    def history(self, employee_id):
        return []

    def email_taken(self, email, exclude_id=None):
        return any(p.email == email and p.id != exclude_id for p in self.people.values())

    def create(self, draft):
        self.created.append(draft)
        return employee(employee_id=99, email=draft.email)

    def update(self, employee_id, draft, *, record_salary_change):
        self.updated.append((employee_id, draft, record_salary_change))
        return employee(employee_id=employee_id, email=draft.email)

    def delete(self, employee_id):
        self.deleted.append(employee_id)
        return employee_id in self.people


def form(**overrides) -> EmployeeInput:
    fields = {
        "full_name": "Ada Lovelace",
        "email": "ada@acme.example",
        "country_code": "DE",
        "department": "Engineering",
        "role": "Engineer",
        "hire_date": "2024-01-15",
        "salary_amount": "85000.00",
    }
    fields.update(overrides)
    return EmployeeInput(**fields)


def test_a_valid_form_reaches_the_store_as_a_draft():
    store = FakeEmployeeStore()

    EmployeeService(store).create(form(email=" New@Acme.example "))

    assert store.created[0].email == "new@acme.example"
    assert store.created[0].salary == Money(Decimal("85000.00"), "EUR")


def test_an_invalid_form_never_reaches_the_store():
    store = FakeEmployeeStore()

    with pytest.raises(InvalidEmployee):
        EmployeeService(store).create(form(salary_amount="-1"))

    assert store.created == []


def test_an_email_someone_else_has_is_refused_on_create():
    store = FakeEmployeeStore(employee(email="ada@acme.example"))

    with pytest.raises(EmailAlreadyUsed):
        EmployeeService(store).create(form(email="ADA@acme.example"))

    assert store.created == []


def test_keeping_your_own_email_on_edit_is_not_a_clash():
    store = FakeEmployeeStore(employee(employee_id=7, email="ada@acme.example"))

    EmployeeService(store).update(7, form(email="ada@acme.example", role="Manager"))

    assert store.updated[0][1].role == "Manager"


def test_taking_a_colleagues_email_on_edit_is_refused():
    store = FakeEmployeeStore(
        employee(employee_id=7), employee(employee_id=8, email="bob@acme.example")
    )

    with pytest.raises(EmailAlreadyUsed):
        EmployeeService(store).update(7, form(email="bob@acme.example"))


def test_a_raise_is_recorded_as_a_salary_change():
    store = FakeEmployeeStore(employee(employee_id=7, amount="85000.00"))

    EmployeeService(store).update(7, form(salary_amount="90000"))

    assert store.updated[0][2] is True


def test_fixing_a_typo_in_a_name_is_not_a_salary_change():
    store = FakeEmployeeStore(employee(employee_id=7, amount="85000.00"))

    EmployeeService(store).update(7, form(full_name="Ada King", salary_amount="85000"))

    assert store.updated[0][2] is False


def test_moving_country_changes_the_currency_so_it_counts_as_a_change():
    store = FakeEmployeeStore(employee(employee_id=7, amount="85000.00"))

    EmployeeService(store).update(7, form(country_code="IN", salary_amount="85000.00"))

    assert store.updated[0][2] is True


def test_editing_someone_who_does_not_exist_is_a_not_found():
    with pytest.raises(EmployeeNotFound):
        EmployeeService(FakeEmployeeStore()).update(404, form())


def test_deleting_someone_who_does_not_exist_is_a_not_found():
    with pytest.raises(EmployeeNotFound):
        EmployeeService(FakeEmployeeStore()).delete(404)


def test_a_detail_view_is_the_employee_and_their_history():
    detail = EmployeeService(FakeEmployeeStore(employee(employee_id=7))).get(7)

    assert detail.employee.id == 7
    assert detail.history == []


def test_looking_up_a_missing_employee_is_a_not_found():
    with pytest.raises(EmployeeNotFound):
        EmployeeService(FakeEmployeeStore()).get(404)
