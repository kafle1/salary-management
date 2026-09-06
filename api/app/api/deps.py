from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.services import DashboardService, EmployeeService
from app.infrastructure.db import get_session_factory
from app.infrastructure.repositories import SqlEmployeeRepository, SqlSalaryAnalytics


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]


def get_employee_service(session: SessionDep) -> EmployeeService:
    return EmployeeService(SqlEmployeeRepository(session))


def get_dashboard_service(session: SessionDep) -> DashboardService:
    return DashboardService(SqlSalaryAnalytics(session))


EmployeeServiceDep = Annotated[EmployeeService, Depends(get_employee_service)]
DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
