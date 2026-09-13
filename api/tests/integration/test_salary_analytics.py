"""The aggregates run in SQL. These tests are what stops that being a leap of faith.

The median in particular is a window function rather than percentile_cont, because the app runs
on Postgres and the suite runs on SQLite. So it gets checked against the pure Python definition in
app.domain.statistics for odd, even and single-row groups.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.filters import EmployeeFilter, GroupBy
from app.domain.insights import BandLayout
from app.domain.statistics import median
from app.infrastructure.models import ExchangeRate
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


def test_a_converted_salary_on_an_exact_half_cent_rounds_up(session: Session):
    """The seeded rates never land on a half cent, so this forces the case they avoid.

    It is the one thing SQLite could get wrong that Postgres would not: the multiply happens in
    the engine, and if the result came back as a float the boundary could fall either way.
    """
    session.add(
        ExchangeRate(
            currency_code="XTS", usd_per_unit=Decimal("0.12345500"), as_of=date(2026, 8, 1)
        )
    )
    session.flush()
    add_employee(session, salary_amount="1000.00", currency_code="XTS")

    stats = analytics(session).overall(EmployeeFilter.build())

    # 1000.00 * 0.123455 is exactly 123.455, and money rounds half up
    assert stats.median_salary == Decimal("123.46")
    assert stats.total_payroll == Decimal("123.46")


def test_lowest_and_highest_pay_are_compared_after_conversion(session: Session):
    add_employee(session, full_name="A", salary_amount="1500.00", currency_code="USD")
    add_employee(session, full_name="B", salary_amount="1000.00", currency_code="EUR")
    add_employee(session, full_name="C", salary_amount="1000.00", currency_code="INR")

    stats = analytics(session).overall(EmployeeFilter.build())

    assert stats.lowest_salary == Decimal("500.00")
    assert stats.highest_salary == Decimal("2000.00")


def test_an_empty_selection_has_no_range(session: Session):
    stats = analytics(session).overall(EmployeeFilter.build(countries=["ZZ"]))

    assert stats.lowest_salary is None
    assert stats.highest_salary is None


def test_each_group_reports_its_own_range(session: Session):
    add_employee(session, full_name="A", department="Sales", salary_amount="30000.00")
    add_employee(session, full_name="B", department="Sales", salary_amount="70000.00")
    add_employee(session, full_name="C", department="Support", salary_amount="50000.00")

    groups = analytics(session).by_group(EmployeeFilter.build(), GroupBy.DEPARTMENT)

    ranges = {g.key: (g.stats.lowest_salary, g.stats.highest_salary) for g in groups}
    assert ranges == {
        "Sales": (Decimal("30000.00"), Decimal("70000.00")),
        "Support": (Decimal("50000.00"), Decimal("50000.00")),
    }


def test_everyone_lands_in_exactly_one_band_and_a_salary_on_an_edge_goes_up(session: Session):
    for index, amount in enumerate(["5000.00", "10000.00", "45000.00"]):
        add_employee(session, full_name=f"P{index}", salary_amount=amount)

    bands = analytics(session).distribution(
        EmployeeFilter.build(), BandLayout(width=Decimal("10000.00"), count=5)
    )

    assert [band.headcount for band in bands] == [1, 1, 0, 0, 1]
    assert bands[1].lower == Decimal("10000.00")


def test_bands_are_counted_after_conversion_and_respect_the_filter(session: Session):
    # 10000 EUR is 20000 USD, so it belongs in the third band, not the second
    add_employee(session, full_name="A", country_code="DE", salary_amount="10000.00",
                 currency_code="EUR")
    add_employee(session, full_name="B", country_code="US", salary_amount="5000.00")

    bands = analytics(session).distribution(
        EmployeeFilter.build(countries=["DE"]), BandLayout(width=Decimal("10000.00"), count=3)
    )

    assert [band.headcount for band in bands] == [0, 0, 1]


def team(session: Session, amounts: list[str], **fields) -> None:
    prefix = f"{fields.get('country_code', 'US')}-{fields.get('role', 'Engineer')}"
    for index, amount in enumerate(amounts):
        add_employee(session, full_name=f"{prefix} {index}", salary_amount=amount, **fields)


def test_someone_under_80_percent_of_their_role_and_country_median_is_flagged(session: Session):
    team(session, ["100000.00"] * 4 + ["79900.00"], role="Engineer")
    # exactly 80% is the line, not over it
    team(session, ["100000.00"] * 4 + ["80000.00"], role="Manager")

    report = analytics(session).below_peers(EmployeeFilter.build(), limit=25)

    assert report.total == 1
    [gap] = report.items
    assert gap.employee.full_name == "US-Engineer 4"
    assert gap.peer_median == Decimal("100000.00")
    assert gap.peers == 5
    assert gap.percent_of_median == 79


def test_a_group_too_small_for_a_fair_median_flags_nobody(session: Session):
    team(session, ["100000.00", "100000.00", "100000.00", "10000.00"])

    assert analytics(session).below_peers(EmployeeFilter.build(), limit=25).total == 0


def test_peers_are_the_same_role_in_the_same_country(session: Session):
    team(session, ["100000.00"] * 5, country_code="US")
    # 100000 INR is 50000 USD, half the US median, but nobody in India is paid under India
    team(session, ["100000.00"] * 5, country_code="IN", currency_code="INR")

    assert analytics(session).below_peers(EmployeeFilter.build(), limit=25).total == 0


def test_a_filter_narrows_who_is_listed_but_not_who_they_are_compared_with(session: Session):
    team(session, ["100000.00"] * 4, department="Engineering")
    add_employee(session, full_name="Sam Sales", department="Sales", salary_amount="70000.00")

    report = analytics(session).below_peers(EmployeeFilter.build(departments=["Sales"]), limit=25)

    assert [gap.employee.full_name for gap in report.items] == ["Sam Sales"]
    assert report.items[0].peers == 5


def test_the_biggest_gaps_come_first_and_the_limit_keeps_the_total(session: Session):
    team(session, ["100000.00"] * 5 + ["60000.00", "70000.00", "50000.00"])

    report = analytics(session).below_peers(EmployeeFilter.build(), limit=2)

    assert report.total == 3
    assert [gap.employee.salary.amount for gap in report.items] == [
        Decimal("50000.00"),
        Decimal("60000.00"),
    ]
