from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import dashboard_router, employees_router, health_router
from app.domain.employee import EmailAlreadyUsed, EmployeeNotFound
from app.domain.employee_draft import InvalidEmployee
from app.domain.filters import InvalidQueryParameter
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Salary Management API",
        version="0.2.0",
        summary="A multi-currency salary book for a 10,000 person org",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    @app.exception_handler(InvalidQueryParameter)
    def _invalid_parameter(_: Request, exc: InvalidQueryParameter) -> JSONResponse:
        # the domain refuses unknown sort fields and groupings, that is a 400 not a 500
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # writes answer with `errors` keyed by field, so the form can put each message under its input
    @app.exception_handler(InvalidEmployee)
    def _invalid_employee(_: Request, exc: InvalidEmployee) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"detail": "Some fields need fixing.", "errors": exc.errors}
        )

    @app.exception_handler(EmailAlreadyUsed)
    def _email_used(_: Request, exc: EmailAlreadyUsed) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(exc),
                "errors": {"email": "Someone else already uses this email."},
            },
        )

    @app.exception_handler(EmployeeNotFound)
    def _not_found(_: Request, exc: EmployeeNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    app.include_router(health_router)
    app.include_router(employees_router)
    app.include_router(dashboard_router)
    return app


app = create_app()
