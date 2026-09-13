"""The only module in the app that knows SQL exists.

Two rules run through all of it:

1. Currency conversion is an expression the database evaluates, not a Python loop. Once that is
   true, sorting by pay, filtering on it and every aggregate stay server-side for free. If it were
   not true, the only way to sort 10,000 employees by USD pay would be to load 10,000 employees.
2. Nothing here is Postgres-only. The app runs on Postgres and the tests run on SQLite, and the
   one place that hurts is the median, which uses a window function instead of percentile_cont.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, case, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.countries import name_for
from app.domain.employee import (
    EmailAlreadyUsed,
    Employee,
    EmployeeNotFound,
    FilterOptions,
    SalaryChange,
)
from app.domain.employee_draft import EmployeeDraft
from app.domain.filters import EmployeeFilter, GroupBy, SortDirection, SortField, SortSpec
from app.domain.insights import (
    MIN_PEERS,
    PEER_GAP_THRESHOLD_PERCENT,
    BandLayout,
    PayBand,
    PeerGap,
    PeerGapReport,
)
from app.domain.money import BASE_CURRENCY, Money, to_cents
from app.domain.pagination import Page, PageRequest
from app.domain.summary import GroupStats, SalaryStats
from app.infrastructure.models import Employee as EmployeeRow
from app.infrastructure.models import ExchangeRate as RateRow
from app.infrastructure.models import SalaryChange as SalaryChangeRow

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

    def get(self, employee_id: int) -> Employee | None:
        row = self._session.execute(
            _employee_select().where(EmployeeRow.id == employee_id)
        ).one_or_none()
        return _to_employee(row) if row is not None else None

    def history(self, employee_id: int) -> list[SalaryChange]:
        rows = self._session.execute(
            select(SalaryChangeRow)
            .where(SalaryChangeRow.employee_id == employee_id)
            .order_by(SalaryChangeRow.changed_on.desc(), SalaryChangeRow.id.desc())
        ).scalars()
        return [_to_salary_change(row) for row in rows]

    def email_taken(self, email: str, exclude_id: int | None = None) -> bool:
        stmt = select(EmployeeRow.id).where(EmployeeRow.email == email)
        if exclude_id is not None:
            stmt = stmt.where(EmployeeRow.id != exclude_id)
        return self._session.execute(stmt.limit(1)).first() is not None

    def create(self, draft: EmployeeDraft) -> Employee:
        with self._saving(draft.email):
            row = EmployeeRow(**_columns(draft))
            self._session.add(row)
            self._session.flush()
            employee_id = row.id
            self._session.add(_salary_change(employee_id, None, draft))
        return self._reload(employee_id)

    def update(
        self, employee_id: int, draft: EmployeeDraft, *, record_salary_change: bool
    ) -> Employee:
        row = self._session.get(EmployeeRow, employee_id)
        if row is None:
            raise EmployeeNotFound(employee_id)
        previous = Money(_as_decimal(row.salary_amount) or Decimal("0"), row.currency_code)
        with self._saving(draft.email, exclude_id=employee_id):
            for column, value in _columns(draft).items():
                setattr(row, column, value)
            if record_salary_change:
                self._session.add(_salary_change(employee_id, previous, draft))
        return self._reload(employee_id)

    def delete(self, employee_id: int) -> bool:
        # the history goes with it through ON DELETE CASCADE
        result = self._session.execute(delete(EmployeeRow).where(EmployeeRow.id == employee_id))
        self._session.commit()
        return result.rowcount > 0

    @contextmanager
    def _saving(self, email: str, exclude_id: int | None = None) -> Iterator[None]:
        try:
            yield
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            # the service already checked, so this is two people saving the same email at once
            if self.email_taken(email, exclude_id):
                raise EmailAlreadyUsed(email) from None
            raise

    def _reload(self, employee_id: int) -> Employee:
        employee = self.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)
        return employee

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
            _employee_select()
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
        headcount, total, lowest, highest = self._session.execute(
            select(*_TOTALS).select_from(EmployeeRow).join(RateRow, _RATE_JOIN).where(*conditions)
        ).one()
        if not headcount:
            return SalaryStats()
        median = self._session.execute(_median_query(conditions)).scalar_one_or_none()
        return _build_stats(int(headcount), total, median, lowest, highest)

    def by_group(self, filters: EmployeeFilter, group_by: GroupBy) -> list[GroupStats]:
        conditions = _conditions(filters)
        column = _GROUP_COLUMNS[group_by]
        totals = self._session.execute(
            select(column, *_TOTALS)
            .select_from(EmployeeRow)
            .join(RateRow, _RATE_JOIN)
            .where(*conditions)
            .group_by(column)
        ).all()
        if not totals:
            return []
        medians = {
            key: median
            for key, median, _ in self._session.execute(_median_query(conditions, column))
        }

        groups = [
            GroupStats(
                key=str(key),
                label=name_for(str(key)) if group_by is GroupBy.COUNTRY else str(key),
                stats=_build_stats(int(headcount), total, medians.get(key), lowest, highest),
            )
            for key, headcount, total, lowest, highest in totals
        ]
        # at most a few dozen groups, so the ordering is cheaper here than a third query
        groups.sort(key=lambda group: (-group.stats.total_payroll, group.key))
        return groups

    def distribution(self, filters: EmployeeFilter, layout: BandLayout) -> list[PayBand]:
        # a CASE over the edges rather than floor(salary / width): floor is not in every SQLite
        # build, and a numeric to integer cast rounds on Postgres but truncates on SQLite
        band = case(
            *[(upper > SALARY_IN_BASE, index) for index, upper in enumerate(layout.upper_edges())],
            else_=layout.count - 1,
        )
        banded = (
            select(band.label("band"))
            .select_from(EmployeeRow)
            .join(RateRow, _RATE_JOIN)
            .where(*_conditions(filters))
            .subquery()
        )
        counts = self._session.execute(
            select(banded.c.band, func.count()).group_by(banded.c.band)
        ).all()
        return layout.bands({int(index): int(headcount) for index, headcount in counts})

    def below_peers(self, filters: EmployeeFilter, limit: int) -> PeerGapReport:
        # the peer median is taken over everyone in the role and country, whatever the filter says.
        # narrowing to one department changes who is listed, never what "normal" means for them
        peers = _median_query([], EmployeeRow.role, EmployeeRow.country_code).subquery()
        matches = (
            _employee_select()
            .add_columns(peers.c.median.label("peer_median"), peers.c.headcount.label("peers"))
            .join(
                peers,
                and_(
                    EmployeeRow.role == peers.c.role,
                    EmployeeRow.country_code == peers.c.country_code,
                ),
            )
            .where(
                *_conditions(filters),
                peers.c.headcount >= MIN_PEERS,
                peers.c.median * PEER_GAP_THRESHOLD_PERCENT > SALARY_IN_BASE * 100,
            )
        )
        total = self._session.execute(
            select(func.count()).select_from(matches.subquery())
        ).scalar_one()
        rows = self._session.execute(
            matches.order_by(SALARY_IN_BASE / peers.c.median, EmployeeRow.id).limit(limit)
        ).all()
        return PeerGapReport(
            total=int(total),
            items=[
                PeerGap(
                    employee=_to_employee(row),
                    peer_median=to_cents(_as_decimal(row.peer_median) or Decimal("0")),
                    peers=int(row.peers),
                )
                for row in rows
            ],
        )


_TOTALS = (
    func.count(),
    func.sum(SALARY_IN_BASE),
    func.min(SALARY_IN_BASE),
    func.max(SALARY_IN_BASE),
)


def _median_query(conditions: list[ColumnElement[bool]], *group_columns: Any) -> Select[Any]:
    """Median without percentile_cont, so the same SQL runs on Postgres and SQLite.

    Number the rows within each group by pay, then keep the middle one or two. The test
    `rn * 2 IN (cnt, cnt + 1, cnt + 2)` picks exactly the middle row when the count is odd and
    exactly the middle pair when it is even, using only integer arithmetic. Doing it with a
    division instead would depend on whether the dialect treats `/` as integer division.

    Selects the group columns under their own names, then `median` and `headcount`.
    """
    partition = list(group_columns)
    ranked = (
        select(
            *[column.label(column.key) for column in group_columns],
            SALARY_IN_BASE.label("value"),
            func.row_number().over(partition_by=partition, order_by=SALARY_IN_BASE).label("rn"),
            func.count().over(partition_by=partition).label("cnt"),
        )
        .select_from(EmployeeRow)
        .join(RateRow, _RATE_JOIN)
        .where(*conditions)
        .subquery()
    )
    middle = ranked.c.rn * 2
    keys = [ranked.c[column.key] for column in group_columns]
    return (
        select(
            *keys,
            func.avg(ranked.c.value).label("median"),
            func.max(ranked.c.cnt).label("headcount"),
        )
        .where(middle.in_([ranked.c.cnt, ranked.c.cnt + 1, ranked.c.cnt + 2]))
        .group_by(*keys)
    )


def _build_stats(headcount: int, total: Any, median: Any, lowest: Any, highest: Any) -> SalaryStats:
    payroll = to_cents(_as_decimal(total) or Decimal("0"))
    return SalaryStats(
        headcount=headcount,
        total_payroll=payroll,
        # derived rather than a second AVG, so the cards on the dashboard always agree
        average_salary=to_cents(payroll / headcount) if headcount else None,
        median_salary=_cents_or_none(median),
        lowest_salary=_cents_or_none(lowest),
        highest_salary=_cents_or_none(highest),
    )


def _cents_or_none(value: Any) -> Decimal | None:
    amount = _as_decimal(value)
    return to_cents(amount) if amount is not None else None


def _employee_select() -> Select[Any]:
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
    )


def _columns(draft: EmployeeDraft) -> dict[str, Any]:
    return {
        "full_name": draft.full_name,
        "email": draft.email,
        "country_code": draft.country_code,
        "department": draft.department,
        "role": draft.role,
        "hire_date": draft.hire_date,
        "salary_amount": draft.salary.amount,
        "currency_code": draft.salary.currency,
    }


def _salary_change(
    employee_id: int, previous: Money | None, draft: EmployeeDraft
) -> SalaryChangeRow:
    return SalaryChangeRow(
        employee_id=employee_id,
        previous_amount=previous.amount if previous else None,
        previous_currency=previous.currency if previous else None,
        new_amount=draft.salary.amount,
        new_currency=draft.salary.currency,
        note=draft.salary_note,
    )


def _to_salary_change(row: SalaryChangeRow) -> SalaryChange:
    previous_amount = _as_decimal(row.previous_amount)
    previous = (
        Money(previous_amount, row.previous_currency)
        if previous_amount is not None and row.previous_currency
        else None
    )
    return SalaryChange(
        changed_on=row.changed_on,
        previous=previous,
        new=Money(_as_decimal(row.new_amount) or Decimal("0"), row.new_currency),
        note=row.note,
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
