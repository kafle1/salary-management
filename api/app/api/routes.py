"""Routers stay thin on purpose: parse the query string, call a service, shape the response."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DashboardServiceDep, EmployeeServiceDep
from app.api.schemas import DashboardSummaryOut, EmployeePageOut, FilterOptionsOut
from app.application.queries import DashboardQuery, EmployeeQuery
from app.domain.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

health_router = APIRouter(tags=["health"])
employees_router = APIRouter(prefix="/employees", tags=["employees"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@health_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@employees_router.get("", response_model=EmployeePageOut)
def list_employees(
    service: EmployeeServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    country: list[str] = Query(default=[]),
    department: list[str] = Query(default=[]),
    role: list[str] = Query(default=[]),
    search: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
) -> EmployeePageOut:
    result = service.list(
        EmployeeQuery(
            countries=country,
            departments=department,
            roles=role,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_dir,
            page=page,
            page_size=page_size,
        )
    )
    return EmployeePageOut.of(result)


@employees_router.get("/filter-options", response_model=FilterOptionsOut)
def filter_options(service: EmployeeServiceDep) -> FilterOptionsOut:
    return FilterOptionsOut.of(service.filter_options())


@dashboard_router.get("/summary", response_model=DashboardSummaryOut)
def dashboard_summary(
    service: DashboardServiceDep,
    group_by: str | None = Query(default=None),
    country: list[str] = Query(default=[]),
    department: list[str] = Query(default=[]),
    role: list[str] = Query(default=[]),
    search: str | None = Query(default=None),
) -> DashboardSummaryOut:
    summary = service.summary(
        DashboardQuery(
            countries=country,
            departments=department,
            roles=role,
            search=search,
            group_by=group_by,
        )
    )
    return DashboardSummaryOut.of(summary)
