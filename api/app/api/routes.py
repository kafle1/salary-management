"""Routers stay thin on purpose: parse the query string, call a service, shape the response."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DashboardServiceDep, EmployeeServiceDep
from app.api.schemas import (
    DashboardSummaryOut,
    EmployeeDetailOut,
    EmployeeIn,
    EmployeeOut,
    EmployeePageOut,
    FilterOptionsOut,
    PayableCountryOut,
)
from app.application.queries import DashboardQuery, EmployeeInput, EmployeeQuery
from app.domain.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

health_router = APIRouter(tags=["health"])
employees_router = APIRouter(prefix="/employees", tags=["employees"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@health_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@health_router.get("/countries", response_model=list[PayableCountryOut], tags=["reference"])
def countries() -> list[PayableCountryOut]:
    return PayableCountryOut.all()


@employees_router.get("", response_model=EmployeePageOut)
def list_employees(
    service: EmployeeServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    country: list[str] | None = Query(default=None),
    department: list[str] | None = Query(default=None),
    role: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
) -> EmployeePageOut:
    result = service.list(
        EmployeeQuery(
            countries=country or [],
            departments=department or [],
            roles=role or [],
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


@employees_router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(body: EmployeeIn, service: EmployeeServiceDep) -> EmployeeOut:
    return EmployeeOut.of(service.create(EmployeeInput(**body.model_dump())))


# after /filter-options, or that path would be read as an id
@employees_router.get("/{employee_id}", response_model=EmployeeDetailOut)
def get_employee(employee_id: int, service: EmployeeServiceDep) -> EmployeeDetailOut:
    return EmployeeDetailOut.of_detail(service.get(employee_id))


@employees_router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, body: EmployeeIn, service: EmployeeServiceDep) -> EmployeeOut:
    return EmployeeOut.of(service.update(employee_id, EmployeeInput(**body.model_dump())))


@employees_router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: int, service: EmployeeServiceDep) -> Response:
    service.delete(employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@dashboard_router.get("/summary", response_model=DashboardSummaryOut)
def dashboard_summary(
    service: DashboardServiceDep,
    group_by: str | None = Query(default=None),
    country: list[str] | None = Query(default=None),
    department: list[str] | None = Query(default=None),
    role: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
) -> DashboardSummaryOut:
    summary = service.summary(
        DashboardQuery(
            countries=country or [],
            departments=department or [],
            roles=role or [],
            search=search,
            group_by=group_by,
        )
    )
    return DashboardSummaryOut.of(summary)
