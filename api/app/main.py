from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import dashboard_router, employees_router, health_router
from app.domain.filters import InvalidQueryParameter
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Salary Management API",
        version="0.1.0",
        summary="Read side of a multi-currency salary book for a 10,000 person org",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.exception_handler(InvalidQueryParameter)
    def _invalid_parameter(_: Request, exc: InvalidQueryParameter) -> JSONResponse:
        # the domain refuses unknown sort fields and groupings, that is a 400 not a 500
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(health_router)
    app.include_router(employees_router)
    app.include_router(dashboard_router)
    return app


app = create_app()
