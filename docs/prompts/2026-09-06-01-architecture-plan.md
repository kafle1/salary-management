# 2026-09-06: architecture plan

The plan the whole build ran from. I wrote the layering and the constraints by hand, then handed
this to the assistant one slice at a time rather than as one big "build me a salary app", because
a single large prompt produces a single large blob and I would spend longer reviewing it than
writing it.

## Prompt given to the assistant

> Set up a FastAPI + SQLAlchemy 2.0 project laid out in four layers with dependencies pointing
> inwards only:
>
> - `domain/`: pure Python. No FastAPI import, no SQLAlchemy import. Money and currency
>   conversion, median, the page-request value object, the sort-field whitelist, the employee
>   filter value object.
> - `application/`: use-case services. They depend on `ports.py`, which is `Protocol` classes,
>   never on a `Session` and never on a repository class directly.
> - `infrastructure/`: SQLAlchemy models, session factory, repositories implementing the ports.
>   The only layer that knows SQL exists.
> - `api/`: routers, Pydantic schemas, dependency wiring. Thin: parse, call a service, return.
>
> Constraints that do not bend:
>
> 1. The app runs on Postgres. The test suite runs on SQLite in-memory. So no Postgres-only SQL
>    anywhere in a query path, including `percentile_cont`, `DISTINCT ON`, and trigram indexes.
> 2. Currency conversion happens in SQL, as a join against a rates table. Never in Python. If it
>    happens in Python then sorting, filtering and aggregating by USD pay all have to happen in
>    Python too, and the whole design collapses into loading the table.
> 3. Pagination is `LIMIT`/`OFFSET` in the database with a separate filtered count. Every sort
>    gets `id` appended as a tie-breaker so page boundaries are stable.
> 4. Sort fields come from an enum mapped to SQL expressions. A user string never reaches the
>    query builder.
> 5. Money is `Decimal` and `NUMERIC` in the schema. No floats in a salary column.
>
> Write the skeleton, no logic yet. I will drive the logic test-first.

## What I kept

The layering, the `Protocol` ports, the settings module, and the split of the repository into
employee and exchange-rate.

## What I rejected

- **A `BaseRepository` generic with `get`/`list`/`create`/`update`/`delete`.** It offered one
  unprompted. There are two repositories and one of them is read-only. A generic base class for
  two concrete cases is an abstraction with nothing to abstract over, and it would have pushed
  the interesting query into a `**kwargs` filter bag where nobody can read it.
- **A `services/` folder holding both use cases and query helpers.** Ended up as `application/`
  with two named services, because "service" as a dumping ground is how a clean layout rots.
- **Repositories returning ORM model instances up into the API layer.** They return domain
  dataclasses. It is one extra mapping function and it is what stops the SQLAlchemy session
  leaking into the response serialisation as a lazy load.
- **`async def` everywhere with an async engine.** It suggested it by default. This workload is
  a handful of short analytic queries per request against a local database. Async buys nothing
  here, and `asyncpg` plus async sessions would have added a whole class of test-fixture problems
  to a two-day build. Sync SQLAlchemy, and FastAPI runs the sync route in a threadpool.
