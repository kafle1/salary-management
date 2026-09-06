"""The aggregates run in SQL. These tests are what stops that being a leap of faith.

The median in particular is a window function rather than percentile_cont, because the app runs
on Postgres and the suite runs on SQLite. So it gets checked against the pure Python definition in
app.domain.statistics for odd, even and single-row groups.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.filters import EmployeeFilter, GroupBy
from app.domain.statistics import median
from app.infrastructure.repositories import SqlSalaryAnalytics
from tests.conftest import add_employee


def analytics(session: Session) -> SqlSalaryAnalytics:
    return SqlSalaryAnalytics(session)


def test_headcount_and_payroll_are_summed_in_the_base_currency(session: Session):
    add_employee(session, full_name="A", salary_amount="100000.00", currency_code="USD")
    add_employee(session, full_name="B", salary_amount="50000.00", currency_code="EUR")
    add_employee(session, full_name="C", salary_amount="200000.00", currency_code="INR")

    stats = analytics(session).overall(EmployeeFilter.build())

    assert stats.headcount == 3
    # 100000*1 + 50000*2 + 200000*0.5
    assert stats.total_payroll == Decimal("300000.00")


def test_average_pay_is_consistent_with_the_total_on_the_same_card(session: Session):
    add_employee(session, full_name="A", salary_amount="100000.00")
    add_employee(session, full_name="B", salary_amount="50000.00")

    stats = analytics(session).overall(EmployeeFilter.build())

    assert stats.average_salary == Decimal("75000.00")
    assert stats.average_salary * stats.headcount == stats.total_payroll


def test_median_of_an_odd_group_matches_the_domain_definition(session: Session):
    amounts = ["40000.00", "90000.00", "50000.00"]
    for index, amount in enumerate(amounts):
        add_employee(session, full_name=f"P{index}", salary_amount=amount)

    stats = analytics(session).overall(EmployeeFilter.build())

    assert stats.median_salary == median([Decimal(a) for a in amounts])
    assert stats.median_salary == Decimal("50000.00")


def test_median_of_an_even_group_matches_the_domain_definition(session: Session):
    amounts = ["40000.00", "90000.00", "50000.00", "60000.00"]
    for index, amount in enumerate(amounts):
        add_employee(session, full_name=f"P{index}", salary_amount=amount)

    stats = analytics(session).overall(EmployeeFilter.build())

    assert stats.median_salary == median([Decimal(a) for a in amounts])
    assert stats.median_salary == Decimal("55000.00")


def test_median_of_one_person_is_that_person(session: Session):
    add_employee(session, salary_amount="123456.00")

    assert analytics(session).overall(EmployeeFilter.build()).median_salary == Decimal("123456.00")


def test_median_is_taken_after_conversion_not_before(session: Session):
    # 1000 EUR is 2000 USD, so the native ordering and the converted ordering disagree
    add_employee(session, full_name="A", salary_amount="1500.00", currency_code="USD")
    add_employee(session, full_name="B", salary_amount="1000.00", currency_code="EUR")
    add_employee(session, full_name="C", salary_amount="1000.00", currency_code="USD")

    stats = analytics(session).overall(EmployeeFilter.build())

    assert stats.median_salary == Decimal("1500.00")


def test_an_empty_selection_reports_zero_rather_than_crashing(session: Session):
    stats = analytics(session).overall(EmployeeFilter.build(countries=["ZZ"]))

    assert stats.headcount == 0
    assert stats.total_payroll == Decimal("0.00")
    assert stats.average_salary is None
    assert stats.median_salary is None


def test_grouping_by_country_reports_a_row_per_country(session: Session):
    add_employee(session, full_name="A", country_code="US", salary_amount="100000.00")
    add_employee(session, full_name="B", country_code="US", salary_amount="200000.00")
    add_employee(session, full_name="C", country_code="IN", salary_amount="100000.00",
                 currency_code="INR")

    groups = analytics(session).by_group(EmployeeFilter.build(), GroupBy.COUNTRY)

    by_key = {group.key: group for group in groups}
    assert set(by_key) == {"US", "IN"}
    assert by_key["US"].stats.headcount == 2
    assert by_key["US"].stats.total_payroll == Decimal("300000.00")
    assert by_key["US"].stats.median_salary == Decimal("150000.00")
    assert by_key["IN"].stats.total_payroll == Decimal("50000.00")


def test_country_groups_carry_a_readable_label(session: Session):
    add_employee(session, country_code="NP", salary_amount="1000.00")

    groups = analytics(session).by_group(EmployeeFilter.build(), GroupBy.COUNTRY)

    assert groups[0].key == "NP"
    assert groups[0].label == "Nepal"


def test_grouping_by_department_and_role(session: Session):
    add_employee(session, full_name="A", department="Sales", role="Account Executive")
    add_employee(session, full_name="B", department="Sales", role="Manager")
    add_employee(session, full_name="C", department="Engineering", role="Manager")

    departments = analytics(session).by_group(EmployeeFilter.build(), GroupBy.DEPARTMENT)
    roles = analytics(session).by_group(EmployeeFilter.build(), GroupBy.ROLE)

    assert {group.key: group.stats.headcount for group in departments} == {
        "Sales": 2,
        "Engineering": 1,
    }
    assert {group.key: group.stats.headcount for group in roles} == {
        "Account Executive": 1,
        "Manager": 2,
    }


def test_groups_come_back_ordered_by_spend_so_the_chart_reads_top_down(session: Session):
    add_employee(session, full_name="A", department="Sales", salary_amount="10000.00")
    add_employee(session, full_name="B", department="Engineering", salary_amount="90000.00")
    add_employee(session, full_name="C", department="Support", salary_amount="50000.00")

    groups = analytics(session).by_group(EmployeeFilter.build(), GroupBy.DEPARTMENT)

    assert [group.key for group in groups] == ["Engineering", "Support", "Sales"]


def test_a_filter_narrows_the_groups_too(session: Session):
    add_employee(session, full_name="A", country_code="US", department="Sales")
    add_employee(session, full_name="B", country_code="IN", department="Sales",
                 currency_code="INR")

    groups = analytics(session).by_group(
        EmployeeFilter.build(countries=["us"]), GroupBy.DEPARTMENT
    )

    assert len(groups) == 1
    assert groups[0].stats.headcount == 1
