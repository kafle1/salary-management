# 2026-09-06 — the domain layer, test first

Money, median, paging and the sort whitelist. All four are small enough that the test is the
specification, so the tests went in first and the assistant wrote against them.

## Prompt

> Here are failing tests for `app/domain/money.py` and `app/domain/statistics.py`. Write the
> minimum that makes them pass.
>
> - `Money` is a frozen dataclass of `Decimal` amount and a 3 letter currency. It normalises the
>   code, refuses anything that is not 3 letters, refuses a negative salary, and quantizes to two
>   places rounding half up.
> - `ExchangeRate` is a currency and `usd_per_unit`. `to_base(money)` refuses a salary in a
>   different currency rather than converting it silently.
> - `median` returns `None` for an empty sequence, the middle value for an odd count, and the
>   rounded mean of the middle pair for an even count.
>
> Do not add a currency registry, do not add arithmetic operators to `Money`, do not add anything
> the tests do not ask for.

## What I kept

All of it, near enough as written.

## What I rejected

- **Banker's rounding.** It reached for `ROUND_HALF_EVEN`, which is the right default for
  repeated statistical work and the wrong one for a payroll figure a human is going to check
  against a spreadsheet. Half up, and there is a one line comment saying why.
- **`Money.__add__`, `__sub__` and `__mul__`.** Offered unprompted. Nothing in this system adds
  two `Money` values in Python, because the adding happens in SQL. Operators nobody calls are
  three more branches to get right and a reader has to check whether they handle mismatched
  currencies.
- **A `Currency` enum of all ISO 4217 codes.** 180 entries to validate 8. The regex is enough.
- **`float` in the median signature** for speed. The whole point of the module is that the numbers
  are exact.

## The one that mattered

I asked it for a median and it gave me `statistics.median` from the standard library. That is the
correct answer for a list in memory, and the wrong answer for this system, because the median has
to be computed over 10,000 rows in the database rather than over a list I have loaded. So the
Python version stayed as the definition and the test oracle, and the real one is a window function
in the repository. The module docstring says exactly that, so the next person does not delete it
as unused.
