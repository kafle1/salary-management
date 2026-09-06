# Prompts and working notes

The brief asks how I collaborate with AI tools, so this folder is the receipt rather than a
claim. Each file is dated and holds the actual prompt or plan I worked from, plus what came back
that I did not keep.

I use an AI coding assistant the way I use a fast junior pair: I write the spec and the shape of
the design, it writes the first draft against a failing test, and I review its output the way I
review a colleague's. The rule I hold to is that the model is never the authority. The test is.
Anything it produced that I could not defend in a review got deleted, and the deletions are
written down here because they are the interesting part.

| File | What it covers |
| --- | --- |
| `2026-09-06-00-clarifications.md` | Questions sent to the reviewer before writing anything, and how the answers changed the scope |
| `2026-09-06-01-architecture-plan.md` | The plan the whole build ran from |
| `2026-09-06-02-domain-and-tests.md` | Money, median and filter validation, test-first |
| `2026-09-06-03-pagination-and-aggregates.md` | The SQL that keeps paging and aggregation server-side |
| `2026-09-06-04-seed-data.md` | Deterministic 10,000-row seed |
| `2026-09-06-05-frontend.md` | Two pages, filter state in the URL |
| `2026-09-06-06-review-pass.md` | Reviewing the assistant's output, and what I threw away |
