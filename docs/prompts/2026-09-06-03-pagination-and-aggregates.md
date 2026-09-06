# 2026-09-06 — pagination and the SQL that keeps aggregates server-side

The graded part. Everything here had a test written before it.

## Prompt

> Implement `SqlEmployeeRepository` and `SqlSalaryAnalytics` against these failing tests.
>
> Non-negotiable:
>
> - The USD figure is `employees.salary_amount * exchange_rates.usd_per_unit`, evaluated by the
>   database, joined on the currency code. Sorting by pay, filtering and every aggregate use that
>   expression. Nothing loads rows into Python to compute it.
> - Paging is `LIMIT` / `OFFSET` plus a separate filtered `COUNT(*)`.
> - Every `ORDER BY` ends with `employees.id`. Two employees with the same name and the same
>   salary must come back in the same order on every request or page 2 will repeat a row from
>   page 1.
> - Median must be correct for odd, even and single-row groups, and must run on both Postgres and
>   SQLite. No `percentile_cont`.
> - The search term is a `LIKE` and must treat `%` and `_` as literals.

## What I kept

The shape: one filter builder shared by the list query, the count and both aggregate queries, so
the table and the dashboard can never disagree about what "filtered" means.

## What I rejected

- **`percentile_cont(0.5) WITHIN GROUP`.** Correct, one line, and Postgres-only. Taking it would
  have meant either two dialect branches or dropping SQLite from the test suite, and the fast
  suite is worth more than the one line. What went in instead numbers the rows by pay and keeps
  the middle one or two.
- **`WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)`**, which was the first version of that. It works
  only if `/` is integer division, which depends on the dialect and on how the query builder types
  the expression. Replaced with `rn * 2 IN (cnt, cnt + 1, cnt + 2)`, which is the same selection
  with no division in it at all. That took a while to see and it is the change I am happiest with.
- **Counting with a window function** (`COUNT(*) OVER ()` on the page query) to save a round trip.
  It looks clever and it makes the database count every matching row while also sorting and
  slicing them. Two simple queries, and the count does not even need the rate join because no
  filter touches that table.
- **Returning ORM objects to the API layer.** The repository selects columns and maps them into a
  frozen domain dataclass. That is what stops a lazy load firing during response serialisation.
- **An `ilike`** for search. Postgres-only again. `func.lower(col).like(...)` behaves the same on
  both.
- **Caching the filter options.** Suggested, and premature. It is three `SELECT DISTINCT`
  queries on an indexed column against a table that changes never.

## Checked, not assumed

The window median was run against `percentile_cont` on the seeded 10,000 row Postgres database.
Both give 44,085.98 for the org-wide median, and the totals match to the cent.
