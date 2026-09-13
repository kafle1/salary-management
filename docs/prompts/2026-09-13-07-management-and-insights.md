# 2026-09-13: managing pay, pay insights, deploy

## Why this slice exists

I re-read the brief a week after the first build. "Manage the salaries data" and "answer
questions about how the org pays people" are two jobs, and the first build only did the second.
An HR manager who has to open a spreadsheet to give someone a raise does not have a salary tool.
So this slice added editing, a pay history, and two answers a dashboard of averages cannot give:
how pay is spread, and who is paid well below their peers.

## What I asked for, in order

Each step started as a failing test, committed on its own as `red:`, then the code as `green:`.

1. **The employee form, in the domain.** Every rule HR can break (blank name, bad email, future
   hire date, a salary with three decimals, a country we do not pay in) returns every error at
   once, not the first one. No FastAPI or SQLAlchemy imports.
2. **The service.** Create, update, delete. Email clash is a 409. Only a real pay move writes a
   history row, so fixing a typo in a name does not show up as a raise.
3. **The repository.** Update and history insert in one commit. History rows go when the person
   goes, through `ON DELETE CASCADE`.
4. **HTTP.** POST, PUT, DELETE, and 422 carrying the field errors the form can show inline.
5. **Insights.** Pay range, pay bands, and people under 80% of the median for their role and
   country, skipping groups under 5.
6. **UI.** shadcn components, charts, an add and edit dialog, a pay history page, a pay review
   page. Writes go through Next.js server actions.
7. **Deploy.** Free tiers: Vercel for both apps, Neon for Postgres.

## Traps I steered around

- **Pay bands as `floor(salary / width)`** is the obvious SQL and it is not portable: `floor` is
  missing from some SQLite builds, and casting a numeric to an integer rounds on Postgres but
  truncates on SQLite. A salary near a band edge could land in one band in the tests and another
  on the live site. Bands are a `CASE` over the band edges instead.
- **Band width exactly highest divided by band count** puts the top earner in an extra band of
  their own. Width is strictly wider, and a test checks the top earner across a range of values.
- **A peer median that follows the page filters** would quietly change "normal pay for a backend
  engineer in India" when you filter to one department. The median is always over the whole role
  and country, and only the list is filtered.
- **Showing "flagged at 80%"** for someone at 79.6% reads like a bug. The share rounds down.
- **Delete on a person who is already gone** counts as done, so a double click or a second tab
  does not show an error.
- **Neon hands out `postgres://` URLs**, which SQLAlchemy maps to psycopg2, and only psycopg 3 is
  installed. Settings rewrite the scheme, with a test for all three spellings.
- **Vercel uploads everything in the folder.** `api/.vercelignore` keeps `.venv` and the tests out
  of the function.

## What I did not take

- **A stored `salary_usd` column** to make sorting by USD pay indexable. It goes stale the moment a
  rate changes, and the sort is 5 ms at this size.
- **`percentile_cont` for the peer median**, for the same reason as on 6 Sep: it would cost the
  fast SQLite test suite.
- **Effective dates on raises.** Still optional per the clarifications, and they add "which salary
  is current today" to every query. History records when a change was saved.

## How it was checked

- 199 tests, under a second.
- On the seeded Postgres and on Neon, the window-function median matches `percentile_cont`:
  43,824.61 both times.
- On the live site: added a person, edited their pay and saw the history row, deleted them, and
  checked headcount went back to 10,000. Checked the pages at phone width.
- Query timings for every endpoint are in [architecture.md](../architecture.md#performance).
