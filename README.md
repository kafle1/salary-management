# Salary Management

A payroll book for a 10,000 person company that pays people in eight countries and eight
currencies, and a dashboard that answers questions about it without anyone rebuilding a pivot
table.

FastAPI and SQLAlchemy over PostgreSQL, Next.js on top, everything paginated and aggregated in
the database.

**Demo video:** _TODO: link_

---

## Run it

One command, assuming Docker is running:

```bash
docker compose up --build
```

- Web: <http://localhost:3000>
- API and interactive docs: <http://localhost:8000/docs>
- Postgres: `localhost:5433` (5433 on purpose, so it does not fight a Postgres you already run)

Compose brings up four things in order: the database, a one-shot `seed` container that creates the
schema and writes exactly 10,000 employees, then the API, then the web app. The seed container
exits when it is done and the API waits for it, so the first page you load already has data on it.

Wiping and starting over is `make down && make up`.

### Without Docker

```bash
make install                 # uv sync for the api, npm install for the web
make seed                    # 10,000 employees, needs a postgres on 5433
make api                     # http://localhost:8000
make web                     # http://localhost:3000
```

Configuration is two environment variables, both with working defaults: `DATABASE_URL` for the
API and `API_BASE_URL` for the web app.

## Test it

```bash
make test     # 108 tests
make lint     # ruff over the api
```

108 tests, about four seconds, no network, no sleeps, no unseeded randomness. They run against
SQLite in memory, which is why they are that fast and why there is no Postgres-only SQL anywhere
in a query path. Splitting them roughly:

- **Unit, no database at all.** Money and currency conversion, the median definition, page
  arithmetic, the sort whitelist, seed determinism, and the two use-case services driven through
  hand-written fakes.
- **Integration, SQLite in memory.** The repositories: page boundaries, tie-breaking, filter
  combinations, `LIKE` escaping, and the aggregate SQL checked against the pure Python median for
  odd, even and single-row groups.
- **API, FastAPI test client.** The response envelope, money serialised as a fixed string, and
  the two error paths that should be a 400 and a 422 rather than a 500.

The one thing SQLite cannot prove is that the same SQL is right on Postgres, so that was checked
by hand against the seeded 10,000 row database: the portable window-function median and
Postgres's own `percentile_cont(0.5)` both return **44,085.98**, and the payroll totals match to
the cent.

## Architecture

Four layers, dependencies pointing inwards only.

```
api/app/
  api/             FastAPI routers, response schemas, dependency wiring
  application/     use cases and the ports they depend on
  domain/          money, median, paging, filters. no framework imports at all
  infrastructure/  sqlalchemy models, session, repositories, the seed
```

`domain/` is plain Python. It holds the things that are worth being sure about in isolation: that
money rounds half up rather than half even, that the median of an even-sized set is the mean of
the middle pair, that page 0 is not a thing, and that the only sortable columns are the eight in
an enum. Nothing in it imports FastAPI or SQLAlchemy, so those tests are microseconds each.

`application/` holds two use cases and depends on `ports.py`, which is a pair of `Protocol`
classes. The services never see a `Session`. That is the seam that lets the service tests run
against a twenty line fake and still assert the interesting thing, which is that a raw query
string turns into the right domain objects before anything touches SQL.

`infrastructure/` is the only place that knows SQL exists, and the only place where the
performance work lives. `api/` is deliberately boring: parse the query string, call a service,
shape the response.

The decision the whole design hangs on is that **currency conversion is an expression the database
evaluates**, `employees.salary_amount * exchange_rates.usd_per_unit`, joined on the currency code.
Once that is true, sorting 10,000 people by what they cost in USD, filtering, and every aggregate
all stay server-side for free. If conversion happened in Python, the only way to sort by USD pay
would be to load every row, and the pagination on top of it would be decorative.

### Pagination and performance

10,000 rows is small and pretending otherwise would be dishonest. What follows is what stays
correct at ten million.

- Paging is `LIMIT` / `OFFSET` in the database, with a separate filtered `COUNT(*)`. The count
  skips the rate join, because no filter touches that table, which leaves it as an index-only
  scan with zero heap fetches.
- **Every sort ends with `id`.** Without a total order, two employees with the same name and the
  same salary can come back in a different order on two requests, and a row silently appears twice
  or not at all across a page boundary. There is a test that fills a table with identical rows to
  pin this.
- Offset is the known limit. Deep offsets scan and discard, so the upgrade is keyset pagination on
  `(sort_key, id)`, which the tie-breaker above is already the groundwork for. It was not built
  because it replaces a page number with a cursor in the public API and 10,000 rows do not justify
  the change.
- The median is a `ROW_NUMBER` / `COUNT` window rather than `percentile_cont`, so the same SQL
  runs on Postgres and on the SQLite the tests use. The middle rows are picked with
  `rn * 2 IN (cnt, cnt + 1, cnt + 2)`, which is the middle one for an odd count and the middle
  pair for an even one, using only integer arithmetic. A division would have depended on whether
  the dialect treats `/` as integer division.
- Average pay is derived from the total and the headcount rather than a second `AVG`, so the
  cards on the dashboard can never disagree with each other by a cent.
- Composite index on `(country_code, department, role)`, which is the exact combination the UI
  sends. On the seeded database a filtered, sorted page comes back on a bitmap index scan and a
  top-N heapsort in about 1.6 ms.
- Free-text search is a `LIKE` and cannot use a btree. That is fine at this size, and the honest
  fix at a larger one is a trigram index, which is Postgres-only and so was left out of a schema
  that also has to build on SQLite.
- Sort fields come from an enum mapped to SQL expressions. A user string never reaches `ORDER BY`.

### Money

Salaries are `NUMERIC(14, 2)` and `Decimal` all the way through, never float. They cross the wire
as a fixed two-place **string**, because a payroll total for 10,000 people does not survive a
round trip through a JSON number, and the browser only needs it for display.

The seeded rates are all chosen so a converted salary lands exactly on a cent. That is not
cosmetic: it means the sum of the rounded rows and the rounded sum of the rows are the same
number, so the KPI card, the country breakdown and a hand check all agree.

### The front end

Two pages, both server components. All filter state lives in the URL, which is what makes
server-side pagination real rather than decorative: page 4 of Engineering in India sorted by pay
is an address you can bookmark, share and go back to, and the server renders it without any client
state to rehydrate. The only client-side JavaScript is the three filter dropdowns and the search
box, which push a new URL.

## What was cut, and why

The reviewer's priority order was clean architecture first, then server-side pagination and
performance across the 10,000 rows, then documentation, all of it above feature count. So this is
the list of things that were deliberately not built. The long version, with the reasoning, is in
[`docs/requirements.md`](docs/requirements.md), which was written and committed before any code.

- **Salary history and effective dates.** My first draft modelled pay as a dated history with a
  window function picking the current row. It was the most interesting query in the system. I
  asked whether it was wanted, was told current salary only, and cut it. Asking first was worth
  more than building it.
- **Natural-language querying.** Confirmed as an optional stretch. A half-finished chat box scores
  worse than none. If it is wanted it goes on as a thin layer that translates a question into the
  same filter parameters the UI already sends, so the model never touches SQL.
- **Authentication.** One persona, one trusted user. It would add schema, middleware and test
  surface without changing a single design decision worth assessing.
- **Payroll execution and localised tax.** Explicitly out of scope, and a different product.
- **Approval workflows and an audit log.** Known patterns, lots of state, no new signal.
- **Live exchange rates.** Seeded, not fetched. A network call would make the tests slow and
  non-deterministic. The rate is one table behind one repository, so a real provider is a
  scheduled job that writes rows.
- **Database migrations.** `create_all` behind an explicit CLI command, never on import. Alembic
  is the right answer the moment a second person has a database and it is the first thing I would
  add on day one of real work. For a repo seeded from empty, it is ceremony.
- **Multi-select filters in the UI.** The API takes repeated `country` / `department` / `role`
  parameters and ORs within a dimension, and there are tests for it. The UI sends one value at a
  time, because a proper multi-select popover is an afternoon of front-end work that demonstrates
  nothing new.

## How AI was used

[`docs/prompts/`](docs/prompts/) has the actual prompts and plans, dated, one file per slice of
the build, each with a section on what came back that I did not keep. The short version is that
the model wrote first drafts against tests I had already written, and the interesting parts are
the rejections: `percentile_cont` because it would have cost the fast test suite, Faker for the
seed because a tuple of names is the whole requirement, a `BaseRepository` generic over two
classes, `Money` arithmetic operators nothing calls, and an integer-division median that was
quietly dialect-dependent.

## Repository layout

```
api/            fastapi service, tests, dockerfile
web/            next.js app
docs/
  requirements.md   written and committed before the first line of code
  prompts/          the prompts this was built from, and what was rejected
docker-compose.yml
Makefile
```
