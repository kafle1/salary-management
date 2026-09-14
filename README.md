# Salary Management

A salary tool for an HR manager at a 10,000 person company that pays people in eight countries.
Change someone's pay and keep its history, then answer "how do we pay people?" without building a
pivot table.

FastAPI and SQLAlchemy over PostgreSQL, Next.js with shadcn on top. Paging, sorting, currency
conversion and every aggregate happen in the database.

- **Live app:** <https://acme-salaries.vercel.app>
- **API docs:** <https://acme-salaries-api.vercel.app/docs>
- **Demo video:** <https://drive.google.com/file/d/1TWSR6B9sTyCRcx6od4TjbbqNenVyDAiG/view>

The live site runs on free tiers. If it has been idle, the first page can take a few seconds to
wake up.

## What it does

**Dashboard.** Headcount, payroll, median, average and pay range in USD, for any mix of country,
department, role and name search. A chart and table break it down by country, department or role,
and a histogram shows how many people sit in each pay band.

**Pay review.** People paid under 80% of the median for the same role in the same country, worst
first. Groups under 5 people are skipped, since a median of three is just someone's salary.

**Employees.** All 10,000, paged, sorted and filtered on the server. Add, edit and delete, with
every form error shown at once. Each person has a pay history: a row when they join and one each
time their pay moves. Fixing a typo in a name is not a pay change, so it writes nothing.

**Money.** Salaries are stored in the person's own currency and converted to USD in SQL through a
seeded rates table. Amounts are `NUMERIC` and `Decimal` end to end and travel as strings.

## Run it

With Docker running:

```bash
docker compose up --build
```

- Web: <http://localhost:3000>
- API and docs: <http://localhost:8000/docs>
- Postgres: `localhost:5433`, so it does not fight a Postgres you already run

Compose starts the database, a one-shot `seed` container that writes exactly 10,000 employees,
then the API and the web app. If a port is taken, override it:
`WEB_PORT=3010 docker compose up --build`. `WEB_PORT`, `API_PORT` and `DB_PORT` all work.

Starting from empty again is `make down && make up`.

### Without Docker

```bash
make install    # uv sync for the api, npm install for the web
make seed       # 10,000 employees, needs a postgres on 5433
make api        # http://localhost:8000
make web        # http://localhost:3000
```

Two settings, both with working defaults: `DATABASE_URL` for the API and `API_BASE_URL` for the
web app.

### Seeding any other database

```bash
cd api
DATABASE_URL='postgres://user:pass@host/db?sslmode=require' uv run salary-admin reset
```

`reset` creates any missing tables, then replaces all data with the same 10,000 people every time.
`postgres://` URLs from hosted providers work as they are.

## Test it

```bash
make test    # 199 tests, under a second
make lint    # ruff over the api
```

No network, no sleeps, no unseeded randomness. Tests run on SQLite in memory, which is why they
are fast and why no query uses Postgres-only SQL.

- **Unit, no database.** Money and rounding, the employee form rules, paging, filters, pay bands,
  the seed, and both services driven through small fakes.
- **Integration, SQLite.** The repositories: page boundaries, tie-breaks, filter combinations,
  `LIKE` escaping, writes with their history rows, and the aggregate SQL checked against a Python
  median.
- **API.** Status codes, the field errors behind a 422, and money serialised as a fixed string.

SQLite cannot prove the SQL is right on Postgres, so that was checked by hand on the seeded data,
locally and on the live Neon database: the window-function median and Postgres's own
`percentile_cont(0.5)` both give **43,824.61**, and payroll totals match to the cent.

## Docs

- [`docs/requirements.md`](docs/requirements.md): goal, scope, what was left out and why. First
  written before any code.
- [`docs/architecture.md`](docs/architecture.md): diagrams, the decisions and what they cost, and
  measured query times for every endpoint on local Postgres and on Neon.
- [`docs/prompts/`](docs/prompts/): the prompts and plans the build ran from, dated, with what I
  threw away.

The short version of the architecture: four layers with imports pointing inwards (`api`,
`application`, `domain`, `infrastructure`). The call everything hangs on is that USD conversion is
`salary_amount * usd_per_unit`, evaluated by the database. That keeps sorting by USD pay, filters
and totals server-side. The slowest endpoint is the pay review list at 36 ms of SQL locally.

## What was left out

The full table with reasons is in the requirements doc.

- **Natural-language questions.** Called an optional stretch. If added, it should turn a question
  into the same filters the UI sends, so the model never writes SQL.
- **Login and roles.** One trusted user. First thing to add for real use.
- **Payroll runs, tax, approvals.** Different products.
- **Effective-dated raises.** History records when a change was saved, not when it takes effect.
- **Live exchange rates.** Seeded, so tests stay fast and repeatable.
- **Migrations.** `create-schema` behind a CLI command. Alembic comes first once a second person
  has a database.
- **Multi-select filters in the UI.** The API already takes repeated `country`, `department` and
  `role` parameters, with tests. The UI sends one value per filter.

## How AI was used

I wrote the spec and the tests, an AI assistant wrote first drafts against them, and I reviewed
the output like a colleague's. [`docs/prompts/`](docs/prompts/) has the receipts. The useful part
is what got rejected: `percentile_cont`, because it would cost the fast test suite; a `floor`-based
pay band that rounds differently on Postgres and SQLite; Faker for the seed; a generic
`BaseRepository` over two classes; and a stored USD column that goes stale when a rate changes.

## Layout

```
api/            fastapi service, admin cli, tests, dockerfile
web/            next.js app
docs/
  requirements.md
  architecture.md
  prompts/
docker-compose.yml
Makefile
```
