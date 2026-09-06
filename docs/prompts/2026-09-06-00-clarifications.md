# 2026-09-06: clarifications, before any code

The brief is deliberately open. Four things in it could each be read two ways, and each reading
implied a different week of work, so they went to the reviewer before I opened an editor. All four
came back the same day.

## What I asked, and what came back

**1. Does "answer questions about how the org pays people" mean structured dashboards, or a
natural-language query box?**

Answer: structured dashboards. KPI cards for total payroll spend, headcount, average and median
pay, plus interactive filters and grouping by country, department and role. A natural-language or
AI-assisted query engine is strictly an optional stretch.

What it changed: the entire product. The role is AI-titled and the MVP is deliberately not an AI
feature, which is the most useful thing I learned all week. I cut the chat box from the plan
before it existed.

**2. Current salary, or a dated revision history?**

Answer: current salary only. Revision logs and effective dates are optional. Say in the
requirements doc what was skipped and why.

What it changed: deleted the whole effective-dated model from my draft requirements doc, which
had `salary_records` with `effective_date` and a window function for "current pay". That was the
single most expensive item on the list and the most fun, which is precisely why asking first was
worth more than building it.

**3. Is multi-currency in scope, and how far does it go?**

Answer: yes, in scope. Each employee's salary is stored in their native currency, plus a
normalised org-wide view converted to one base currency through a simple seeded exchange-rate
table. Localised payroll tax math is explicitly out.

What it changed: confirmed the seeded-rate table rather than a live rate provider, and confirmed I
should not go anywhere near tax.

**4. Does it need to be deployed live, or is a repo with Docker Compose plus a video enough?**

Answer: deployment is not a blocker. A live URL on a free tier and a clean repo with a working
Compose setup plus the demo video are weighted equally. Pick whichever ships sooner.

What it changed: Compose plus video. It ships sooner and it is the artifact a reviewer can
actually read.

## Also settled

Priority order, in the reviewer's words: clean code architecture first, then server-side
pagination and performance across the 10,000-employee dataset, then clear documentation, all of
it above feature count. Six to eight hours of focused effort. Requirements doc before code.

So the two ways to lose here are over-building and shipping without the doc that frames the cuts
as decisions. The plan is written against that.
