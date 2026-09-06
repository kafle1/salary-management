"""Service tests with hand-written fakes and no database.

This is the whole point of the ports: the rules about how a request turns into a query are worth
testing, and none of them need SQL to be true.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.queries import DashboardQuery, EmployeeQuery
from app.application.services import DashboardService, EmployeeService
from app.domain.employee import FilterOptions
from app.domain.filters import (
    EmployeeFilter,
    GroupBy,
    SortDirection,
    SortField,
    UnknownGroupBy,
    UnknownSortField,
)
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
