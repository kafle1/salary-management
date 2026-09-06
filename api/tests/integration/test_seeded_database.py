"""Seed into a real schema and read it back through the repositories.

This is the one place the whole read path is exercised end to end: seed writes native amounts,
the join converts them, and the aggregates land on the same numbers a manual pass over the rows
would give.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.filters import EmployeeFilter, GroupBy, SortDirection, SortField, SortSpec
from app.domain.money import to_cents
from app.domain.pagination import PageRequest
from app.domain.statistics import median
from app.infrastructure.models import Employee as EmployeeRow
from app.infrastructure.repositories import SqlEmployeeRepository, SqlSalaryAnalytics
from app.infrastructure.seed import USD_PER_UNIT, generate_employees, seed_all

SAMPLE = 600


def seeded(session: Session) -> Session:
    seed_all(session, count=SAMPLE)
    session.commit()
    return session


def expected_usd_amounts() -> list[Decimal]:
    """Exact products, not pre-rounded. The SQL rounds once at the end and so should the oracle."""
    return [
        row["salary_amount"] * USD_PER_UNIT[row["currency_code"]]
        for row in generate_employees(count=SAMPLE)
    ]


def test_the_seed_writes_every_row_it_generated(session: Session):
    seeded(session)

    assert session.execute(select(func.count()).select_from(EmployeeRow)).scalar_one() == SAMPLE


def test_seeding_twice_leaves_one_copy_not_two(session: Session):
    seed_all(session, count=SAMPLE)
    seed_all(session, count=SAMPLE)
    session.commit()

    assert session.execute(select(func.count()).select_from(EmployeeRow)).scalar_one() == SAMPLE


def test_payroll_and_median_match_a_hand_rolled_pass_over_the_same_rows(session: Session):
    seeded(session)
    amounts = expected_usd_amounts()

    stats = SqlSalaryAnalytics(session).overall(EmployeeFilter.build())

    assert stats.headcount == SAMPLE
    assert stats.total_payroll == to_cents(sum(amounts, Decimal("0")))
    assert stats.median_salary == to_cents(median(amounts))


def test_the_median_sits_below_the_mean_because_the_pyramid_is_top_heavy(session: Session):
    seeded(session)

    stats = SqlSalaryAnalytics(session).overall(EmployeeFilter.build())

    assert stats.median_salary < stats.average_salary


def test_country_groups_add_back_up_to_the_org_total(session: Session):
    seeded(session)
    analytics = SqlSalaryAnalytics(session)

    overall = analytics.overall(EmployeeFilter.build())
    groups = analytics.by_group(EmployeeFilter.build(), GroupBy.COUNTRY)

    assert sum(group.stats.headcount for group in groups) == overall.headcount
    assert sum(
        (group.stats.total_payroll for group in groups), Decimal("0")
    ) == overall.total_payroll


def test_paging_the_whole_seeded_set_visits_every_row_exactly_once(session: Session):
    seeded(session)
    repository = SqlEmployeeRepository(session)
    sort = SortSpec(SortField.SALARY_USD, SortDirection.DESC)

    seen: list[int] = []
    page_number = 1
    while True:
        page = repository.list_employees(
            EmployeeFilter.build(), sort, PageRequest(page=page_number, page_size=100)
        )
        seen.extend(employee.id for employee in page.items)
        if not page.has_next:
            break
        page_number += 1

    assert len(seen) == SAMPLE
    assert len(set(seen)) == SAMPLE


def test_the_top_of_the_converted_ranking_is_not_the_top_of_the_native_one(session: Session):
    seeded(session)
    repository = SqlEmployeeRepository(session)

    by_usd = repository.list_employees(
        EmployeeFilter.build(),
        SortSpec(SortField.SALARY_USD, SortDirection.DESC),
        PageRequest(1, 5),
    )
    by_native = repository.list_employees(
        EmployeeFilter.build(),
        SortSpec(SortField.SALARY_NATIVE, SortDirection.DESC),
        PageRequest(1, 5),
    )

    # the biggest raw numbers are all in the weakest currencies, so these lists disagree
    assert [e.id for e in by_usd.items] != [e.id for e in by_native.items]
