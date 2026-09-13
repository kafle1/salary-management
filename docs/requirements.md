# Salary Management: requirements

Written on 6 Sep before any code, after Sandli answered my scoping questions
([clarifications](prompts/2026-09-06-00-clarifications.md)). Revised on 13 Sep, see "What changed".

## Goal

ACME's HR manager keeps pay for 10,000 people in eight countries in spreadsheets. They should be
able to keep that data in one web app and answer "how do we pay people?" without building a pivot
table. Two jobs, in this order: **answer questions about pay**, then **change pay safely**.

## Who it is for

One HR manager. A trusted internal user, not a portal employees log into.

## In scope

**Answering questions**
- Dashboard for any filter of country, department, role and name: headcount, payroll, median,
  average and pay range, all in USD.
- Breakdown by country, department or role, as a chart and a table.
- How pay is spread: people per pay band.
- Pay review list: people paid under 80% of the median for the same role in the same country.
  Groups under 5 people are skipped, since a median of three is one person's salary.

**Managing people and pay**
- Employee list with server-side paging, sorting, filters and search.
- Add, edit and delete a person. Every form error comes back at once.
- Pay history per person. A row is written when someone is added and each time their pay moves.
  A fixed typo in a name is not a pay change, so it writes nothing.

**Money**
- Salary stored in the person's own currency, never overwritten with a converted value.
- A seeded exchange-rate table converts to USD inside the database, so sorting and totals by USD
  stay server-side.

**Data and quality**
- Seed script: exactly 10,000 people, same data every run.
- Fast, deterministic tests. Deployed on free tiers, and runnable with one Docker command.

## Left out, and why

| Left out | Why |
| --- | --- |
| Natural-language questions | Sandli called it an optional stretch. A half-built chat box is worse than none. If added, it should turn a question into the same filters the UI sends, so the model never writes SQL. |
| Login and roles | One trusted user. It adds a lot of code and tests without changing any design decision here. First thing to add for real use, through the company's SSO. |
| Payroll runs and tax | Sandli ruled out local tax. It is a different product with rules per country. |
| Approvals on pay changes | Real HR tools need a second approver. It is process modelling, and it would multiply the states in the domain. |
| Future-dated raises | History records when a change was saved, not when it takes effect. Effective dates were optional, and they add "which salary is current today" to every query. |
| Live exchange rates | Rates are seeded. A network call would make tests slow and flaky. Rates sit in one table, so a real feed is a job that writes rows. |
| Migrations | Schema comes from an explicit `create-schema` command. Alembic is the first thing to add once a second person has a database. |
| Bulk import from Excel | Useful for day one, but the seed script covers loading data for this exercise. |

## What changed on 13 Sep

The first version of this doc cut editing and pay history to keep the build small. Reading the
brief again, "manage the salaries data" means HR has to change pay in the app, not only look at it.
So editing, deleting and the pay history went in, along with the pay bands and the pay review
list. The core rules did not change: aggregates stay in SQL, money stays exact, and tests stay fast.

## Done means

- Live app and API, plus `docker compose up` for a local copy.
- `salary-admin reset` loads the same 10,000 people every time.
- Tests run in about a second, with no network, no sleeps and no unseeded randomness.
- Commit history shows the order it was built in, tests before code.
- A short video walking through the app.

Design, tradeoffs and measured performance are in [architecture.md](architecture.md).
