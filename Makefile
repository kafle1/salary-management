DB_URL ?= postgresql+psycopg://salary:salary@localhost:5433/salary_management

.PHONY: up down logs test seed api web install

## everything, one command
up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f api web

## the tests. sqlite in memory, no containers needed
test:
	cd api && uv run pytest

install:
	cd api && uv sync
	cd web && npm install

## local development against the compose database on 5433
seed:
	cd api && DATABASE_URL=$(DB_URL) uv run salary-admin reset

api:
	cd api && DATABASE_URL=$(DB_URL) uv run uvicorn app.main:app --reload --port 8000

web:
	cd web && API_BASE_URL=http://127.0.0.1:8000 npm run dev
