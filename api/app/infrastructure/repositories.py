"""The only module in the app that knows SQL exists.

Two rules run through all of it:

1. Currency conversion is an expression the database evaluates, not a Python loop. Once that is
   true, sorting by pay, filtering on it and every aggregate stay server-side for free. If it were
   not true, the only way to sort 10,000 employees by USD pay would be to load 10,000 employees.
2. Nothing here is Postgres-only. The app runs on Postgres and the tests run on SQLite, and the
   one place that hurts is the median, which uses a window function instead of percentile_cont.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.countries import name_for
from app.domain.employee import Employee, FilterOptions
from app.domain.filters import EmployeeFilter, GroupBy, SortDirection, SortField, SortSpec
from app.domain.money import BASE_CURRENCY, Money, to_cents
from app.domain.pagination import Page, PageRequest
from app.domain.summary import GroupStats, SalaryStats
from app.infrastructure.models import Employee as EmployeeRow
from app.infrastructure.models import ExchangeRate as RateRow

SALARY_IN_BASE = EmployeeRow.salary_amount * RateRow.usd_per_unit

_RATE_JOIN = EmployeeRow.currency_code == RateRow.currency_code

_SORT_COLUMNS: dict[SortField, Any] = {
    SortField.NAME: EmployeeRow.full_name,
    SortField.EMAIL: EmployeeRow.email,
    SortField.COUNTRY: EmployeeRow.country_code,
    SortField.DEPARTMENT: EmployeeRow.department,
    SortField.ROLE: EmployeeRow.role,
    SortField.HIRE_DATE: EmployeeRow.hire_date,
    SortField.SALARY_NATIVE: EmployeeRow.salary_amount,
    SortField.SALARY_USD: SALARY_IN_BASE,
}

_GROUP_COLUMNS: dict[GroupBy, Any] = {
    GroupBy.COUNTRY: EmployeeRow.country_code,
    GroupBy.DEPARTMENT: EmployeeRow.department,
    GroupBy.ROLE: EmployeeRow.role,
}


def _escape_like(term: str) -> str:
    """Without this, searching for "100%" returns the whole company."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _conditions(filters: EmployeeFilter) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.countries:
        conditions.append(EmployeeRow.country_code.in_(filters.countries))
    if filters.departments:
        conditions.append(EmployeeRow.department.in_(filters.departments))
    if filters.roles:
        conditions.append(EmployeeRow.role.in_(filters.roles))
    if filters.search:
        pattern = f"%{_escape_like(filters.search.lower())}%"
        conditions.append(
            or_(
                func.lower(EmployeeRow.full_name).like(pattern, escape="\\"),
                func.lower(EmployeeRow.email).like(pattern, escape="\\"),
            )
        )
    return conditions


def _as_decimal(value: Any) -> Decimal | None:
    """Postgres hands back Decimal, SQLite hands back float. Normalise before any money maths."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class SqlEmployeeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_employees(
        self, filters: EmployeeFilter, sort: SortSpec, page: PageRequest
    ) -> Page[Employee]:
        conditions = _conditions(filters)
        total = self._count(conditions)
        rows = self._session.execute(self._page_query(conditions, sort, page)).all()
        return Page(items=[_to_employee(row) for row in rows], total=total, request=page)

    def filter_options(self) -> FilterOptions:
        countries = self._distinct(EmployeeRow.country_code)
        return FilterOptions(
            countries=[(code, name_for(code)) for code in countries],
            departments=self._distinct(EmployeeRow.department),
            roles=self._distinct(EmployeeRow.role),
        )

    def _count(self, conditions: list[ColumnElement[bool]]) -> int:
        # no filter touches the rates table, so the count does not pay for the join
        stmt = select(func.count()).select_from(EmployeeRow).where(*conditions)
        return int(self._session.execute(stmt).scalar_one())

    def _page_query(
        self, conditions: list[ColumnElement[bool]], sort: SortSpec, page: PageRequest
    ) -> Select[Any]:
        column = _SORT_COLUMNS[sort.field]
        ordering = column.desc() if sort.direction is SortDirection.DESC else column.asc()
        return (
            select(
                EmployeeRow.id,
                EmployeeRow.full_name,
                EmployeeRow.email,
                EmployeeRow.country_code,
                EmployeeRow.department,
                EmployeeRow.role,
                EmployeeRow.hire_date,
                EmployeeRow.salary_amount,
                EmployeeRow.currency_code,
                SALARY_IN_BASE.label("salary_in_base"),
            )
            .select_from(EmployeeRow)
            .join(RateRow, _RATE_JOIN)
            .where(*conditions)
            # id last, always. without a total order two pages of the same query can overlap.
            .order_by(ordering, EmployeeRow.id.asc())
            .limit(page.limit)
            .offset(page.offset)
        )

    def _distinct(self, column: Any) -> list[str]:
        stmt = select(column).distinct().order_by(column)
        return list(self._session.execute(stmt).scalars().all())


class SqlSalaryAnalytics:
    def __init__(self, session: Session) -> None:
        self._session = session

    def overall(self, filters: EmployeeFilter) -> SalaryStats:
        conditions = _conditions(filters)
        headcount, total = self._session.execute(
            select(func.count(), func.sum(SALARY_IN_BASE))
            .select_from(EmployeeRow)
            .join(RateRow, _RATE_JOIN)
            .where(*conditions)
        ).one()
        if not headcount:
            return SalaryStats()
        median = self._session.execute(self._median_query(conditions)).scalar_one_or_none()
        return _build_stats(int(headcount), _as_decimal(total), _as_decimal(median))

    def by_group(self, filters: EmployeeFilter, group_by: GroupBy) -> list[GroupStats]:
        conditions = _conditions(filters)
        column = _GROUP_COLUMNS[group_by]
        totals = self._session.execute(
            select(column, func.count(), func.sum(SALARY_IN_BASE))
            .select_from(EmployeeRow)
            .join(RateRow, _RATE_JOIN)
            .where(*conditions)
            .group_by(column)
        ).all()
        if not totals:
            return []
        medians = dict(self._session.execute(self._median_query(conditions, column)).all())

        groups = [
            GroupStats(
                key=str(key),
                label=name_for(str(key)) if group_by is GroupBy.COUNTRY else str(key),
                stats=_build_stats(
                    int(headcount), _as_decimal(total), _as_decimal(medians.get(key))
                ),
            )
            for key, headcount, total in totals
        ]
        # at most a few dozen groups, so the ordering is cheaper here than a third query
        groups.sort(key=lambda group: (-group.stats.total_payroll, group.key))
        return groups

    def _median_query(
        self, conditions: list[ColumnElement[bool]], group_column: Any | None = None
    ) -> Select[Any]:
        """Median without percentile_cont, so the same SQL runs on Postgres and SQLite.

        Number the rows within each group by pay, then keep the middle one or two. The test
        `rn * 2 IN (cnt, cnt + 1, cnt + 2)` picks exactly the middle row when the count is odd and
        exactly the middle pair when it is even, using only integer arithmetic. Doing it with a
        division instead would depend on whether the dialect treats `/` as integer division.
        """
        partition = [group_column] if group_column is not None else []
        selected: list[Any] = [SALARY_IN_BASE.label("value")]
        if group_column is not None:
            selected.insert(0, group_column.label("grp"))
        ranked = (
            select(
                *selected,
                func.row_number()
                .over(partition_by=partition, order_by=SALARY_IN_BASE)
                .label("rn"),
                func.count().over(partition_by=partition).label("cnt"),
            )
            .select_from(EmployeeRow)
            .join(RateRow, _RATE_JOIN)
            .where(*conditions)
            .subquery()
        )
        middle = ranked.c.rn * 2
        keep = middle.in_([ranked.c.cnt, ranked.c.cnt + 1, ranked.c.cnt + 2])
        if group_column is None:
            return select(func.avg(ranked.c.value)).where(keep)
        return (
            select(ranked.c.grp, func.avg(ranked.c.value)).where(keep).group_by(ranked.c.grp)
        )


def _build_stats(headcount: int, total: Decimal | None, median: Decimal | None) -> SalaryStats:
    payroll = to_cents(total or Decimal("0"))
    return SalaryStats(
        headcount=headcount,
        total_payroll=payroll,
        # derived rather than a second AVG, so the cards on the dashboard always agree
        average_salary=to_cents(payroll / headcount) if headcount else None,
        median_salary=to_cents(median) if median is not None else None,
    )


def _to_employee(row: Any) -> Employee:
    return Employee(
        id=row.id,
        full_name=row.full_name,
        email=row.email,
        country_code=row.country_code,
        country_name=name_for(row.country_code),
        department=row.department,
        role=row.role,
        hire_date=row.hire_date,
        salary=Money(_as_decimal(row.salary_amount) or Decimal("0"), row.currency_code),
        salary_in_base=Money(_as_decimal(row.salary_in_base) or Decimal("0"), BASE_CURRENCY),
    )
