# Salary Management: requirements

Written before the code. Updated once, on 6 Sep, after the reviewer answered the clarifying
questions (see `docs/prompts/2026-09-06-00-clarifications.md`). Where this doc and those answers
disagreed, the answers won.

## Goal

Give ACME's HR manager one place to see and reason about what the organisation pays its
10,000 employees across several countries and currencies, replacing the spreadsheets they
maintain by hand.

The pain in the brief is not data entry. It is that nobody can answer questions about pay without
rebuilding a pivot table. So the system is read-heavy, and the value sits in the aggregate view
rather than in the forms.

## Who it is for

A single HR manager. One trusted user inside the company, not a portal that employees log into.
That assumption drives most of what is left out below.

## Scope

**Employee and salary data**

- Employee record: name, email, country, department, role, hire date.
- **Current salary only.** One amount, one currency, held on the employee row. Revision history
  and effective dates were confirmed optional and are cut. See "Deliberately out of scope".
- Multi-currency held honestly. The amount is stored exactly as the employee is paid, in their
  own currency. A seeded exchange-rate table converts to a single base currency (USD) for any
  view that compares people across countries. The stored amount is never overwritten with a
  converted one.

**Answering questions about pay**

- Employee list with server-side pagination, sorting and filtering by country, department and
  role, plus a free-text search over name and email.
- Dashboard KPI cards for the current filter selection: headcount, total payroll spend in USD,
  average pay, median pay.
- The same four figures broken down by a chosen dimension: country, department or role.
- Every number above is computed in SQL, including the currency conversion. The API never loads
  10,000 rows into Python to add them up.

**Seeding**

- Deterministic seed script producing 10,000 employees spread across 8 countries, 8 departments
  and 10 roles, with pay scaled by country and role so the dashboard has real shape to it.
  Fixed RNG seed, so two runs produce byte-identical data.

## Deliberately out of scope

Each of these is real work that would not tell you anything more about my engineering judgment.

- **Salary history and effective dates.** The original draft of this doc modelled pay as a dated
  history with a window function picking the current row. The reviewer confirmed current salary
  only, history optional, so it is cut. It was the most interesting query in the system and the
  most expensive thing to build, which is exactly why it needed an answer before I started rather
  than after. The upgrade path is a `salary_revisions` table and one `DISTINCT ON`
  (or `ROW_NUMBER`) view feeding the same repository interface; nothing above the repository
  changes.
- **Natural-language / AI-assisted querying.** Confirmed as an optional stretch. A half-finished
  chat box scores worse than none, so the structured dashboard is the product. If it is wanted
  later it goes on as a thin translation layer that turns a question into the same filter
  parameters the UI already sends, so the model never touches SQL and every answer stays
  reproducible without it.
- **Authentication, roles and permissions.** One persona, one trusted user. Auth is
  well-understood plumbing and would add schema, middleware and test surface without changing a
  single design decision being assessed here. In production it is the first thing I would add,
  behind the company's existing SSO.
- **Payroll execution and localised tax.** No tax, deductions, payslips or payment runs, and the
  reviewer put localised payroll tax explicitly out of scope. That is a different product with a
  per-country compliance surface.
- **Approval workflows.** No maker-checker on a salary change. Real HR software needs it. It is
  process modelling rather than engineering judgment, and it would multiply the states in the
  domain.
- **Live exchange rates.** Rates are seeded, not fetched. A network call would make tests slow and
  non-deterministic, which the brief asks against. The rate lives in one table read through one
  repository, so swapping in a real provider is a scheduled job that writes rows, not a rewrite.
- **Audit log.** No `who changed what` table. Same reasoning as history: it is a known pattern and
  it costs schema and test surface without adding signal.
- **Database migrations.** Schema is created with SQLAlchemy `create_all` behind an explicit CLI
  command. Alembic is the correct answer the moment a second person has a database, and it is the
  first thing I would add on day one of real work. For a repo that is seeded from empty every
  time, it is ceremony.
- **Employee self-service, notifications, org chart, manager hierarchy.** The manager field from
  the first draft is gone too. The reviewer named country, department and role as the grouping
  dimensions, and a fourth one that nothing groups by is dead weight.

## Architecture

Four layers, dependencies pointing inwards only.

```
api/          FastAPI routers, request/response schemas, dependency wiring
application/  use cases: employee listing, dashboard summary. Depends on ports, not on SQL
domain/       pure Python: money, currency conversion, median, filters, paging. No framework
infrastructure/ SQLAlchemy models, session, repositories that implement the ports
```

- `domain/` imports nothing from FastAPI or SQLAlchemy. It holds the rules that are worth testing
  in isolation: what a valid page request is, which columns may be sorted on, how money rounds,
  what the median of an even-sized set is.
- `application/` depends on `ports.py`, a pair of `Protocol` classes. The services never see a
  `Session`. That is what makes the service tests run with a hand-written fake repository and no
  database at all.
- `infrastructure/` is the only place that knows SQL exists.
- `api/` is thin on purpose. A router function should read as: parse input, call a service,
  return it.

The point of the split is that the expensive knowledge (the SQL that keeps aggregates
server-side) is isolated behind an interface, and the cheap knowledge (rounding, validation,
whitelisting) is testable without booting anything.

## Performance

10,000 rows is small, and pretending otherwise would be dishonest. What follows is what stays
correct when the number is 10,000,000, since that is the part actually being assessed.

- **Pagination happens in the database.** `LIMIT` / `OFFSET` with a separate filtered `COUNT(*)`.
  The API accepts `page` and `page_size`, a `page_size` above 200 is rejected rather than quietly
  reduced, and the response carries `total`, `total_pages` and `has_next` so the UI never needs
  the full set to render controls.
- **Ordering is total, not partial.** Every sort appends `id` as a final tie-breaker. Without it,
  Postgres is free to return rows in a different order for two pages of the same query and
  records silently appear twice or not at all across page boundaries.
- **Offset is the known limit.** Deep offsets scan and discard. At 10,000 rows the last page costs
  nothing; at 10,000,000 it would, and the fix is keyset pagination on `(sort_key, id)`. I did
  not build it because it changes the API contract (a cursor instead of a page number) and the
  dataset in the brief does not justify it. The tie-breaker above is the groundwork for it.
- **Currency conversion is a join, not a loop.** `employees` joins `exchange_rates` on the
  currency code and the USD figure is `amount * usd_per_unit` evaluated by the database. This is
  the decision that keeps everything else server-side: if conversion happened in Python, then
  sorting by USD pay, filtering on it, and every aggregate would have to happen in Python too,
  and the whole thing would collapse into loading the table.
- **Aggregates are one query per card, not one per row.** `COUNT`, `SUM` and `AVG` of the
  converted expression, grouped in SQL.
- **Median is computed in SQL and stays portable.** Postgres has
  `percentile_cont(0.5) WITHIN GROUP`, which SQLite does not, and the test suite runs on SQLite
  in-memory to stay fast. Rather than keep two dialect-specific code paths for one number, median
  uses a `ROW_NUMBER() / COUNT() OVER` window that both engines run natively, and a unit test
  asserts the SQL result matches a pure-Python median for odd, even and single-row groups.
- **Indexes.** A composite index on `(country_code, department, role)` covering the filter
  combination the UI actually sends, plus an index on `currency_code` for the rate join. Free-text
  search is a `LIKE` scan and cannot use a btree. That is fine at this size and the honest fix at
  a larger one is a trigram index, which is Postgres-specific and therefore was not added to a
  schema that has to build on SQLite for tests.
- **Sort input is whitelisted**, mapped from a small enum to a SQL expression. User strings never
  reach the query builder.

## Stack, and why

- **Python + FastAPI + SQLAlchemy 2.0 + PostgreSQL.** Python and React were named in the role.
  Postgres because the multi-currency aggregate work is the interesting part and it should run on
  the engine it would run on in production.
- **SQLite in-memory for tests only.** It keeps the suite in the low seconds with no container, and
  it costs one real constraint: no Postgres-only SQL. That constraint is what forced the portable
  median above, and I consider that a fair trade. Docker Compose runs the app on Postgres.
- **Next.js + TypeScript** for the UI, two pages, server components reading the filter state
  straight out of the URL. Filter state living in the URL is what makes server-side pagination
  honest: a page link is a real link, shareable and back-button-correct.
- **uv** for Python dependency management.

## What "done" looks like

- `docker compose up` gives a working database, API and web app.
- `make seed` puts exactly 10,000 employees in it, identically every time.
- The test suite runs in seconds, with no network, no sleeps and no unseeded randomness.
- Commit history shows the order this was actually built in.
- A short video walking through the dashboard and the employee table.
