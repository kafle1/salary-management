import { FilterBar } from "@/components/filter-bar";
import { GroupBySelect } from "@/components/group-by-select";
import {
  describeError,
  fetchFilterOptions,
  fetchSummary,
  type DashboardSummary,
  type FilterOptions,
} from "@/lib/api";
import { compactMoney, count, money, percent } from "@/lib/format";
import { first, toApiParams, type RawSearchParams } from "@/lib/query";

// filters live in the url, so every render is a fresh answer to a specific question
export const dynamic = "force-dynamic";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<RawSearchParams>;
}) {
  const params = await searchParams;
  const groupBy = first(params, "group_by") || "country";

  let summary: DashboardSummary;
  let options: FilterOptions;
  try {
    [summary, options] = await Promise.all([
      fetchSummary(toApiParams(params, { group_by: groupBy })),
      fetchFilterOptions(),
    ]);
  } catch (error) {
    return (
      <>
        <h1>Payroll overview</h1>
        <p className="error">
          Could not load this view. If nothing is running, start the stack with{" "}
          <code>docker compose up</code>. ({describeError(error)})
        </p>
      </>
    );
  }

  const { overall, groups, base_currency: base } = summary;
  const biggest = groups[0]?.total_payroll ?? "0";

  return (
    <>
      <h1>Payroll overview</h1>
      <p className="lede">
        Everything is normalised to {base} through the seeded rate table. Filters apply to the cards
        and the breakdown together.
      </p>

      <FilterBar basePath="/" params={params} options={options}>
        <GroupBySelect params={params} />
      </FilterBar>

      <section className="kpis">
        <article className="kpi">
          <div className="label">Headcount</div>
          <div className="value">{count(overall.headcount)}</div>
          <div className="note">people in this selection</div>
        </article>
        <article className="kpi">
          <div className="label">Total payroll spend</div>
          <div className="value" title={money(overall.total_payroll, base, 2)}>
            {compactMoney(overall.total_payroll, base)}
          </div>
          <div className="note">{money(overall.total_payroll, base)} per year</div>
        </article>
        <article className="kpi">
          <div className="label">Average pay</div>
          <div className="value">{money(overall.average_salary, base)}</div>
          <div className="note">mean, pulled up by the top of the org</div>
        </article>
        <article className="kpi">
          <div className="label">Median pay</div>
          <div className="value">{money(overall.median_salary, base)}</div>
          <div className="note">what a typical person here earns</div>
        </article>
      </section>

      <div className="panel">
        <div className="panel-head">
          <span>Broken down by {summary.group_by}</span>
          <span>{groups.length} groups, ordered by spend</span>
        </div>
        {groups.length === 0 ? (
          <p className="empty">No one matches these filters.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{summary.group_by}</th>
                <th className="num">Headcount</th>
                <th className="num">Total spend</th>
                <th>Share</th>
                <th className="num">Average</th>
                <th className="num">Median</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.key}>
                  <td className="name">{group.label}</td>
                  <td className="num">{count(group.headcount)}</td>
                  <td className="num">{money(group.total_payroll, base)}</td>
                  <td>
                    <div
                      className="bar"
                      title={`${percent(group.total_payroll, overall.total_payroll).toFixed(1)}% of total spend`}
                    >
                      <span style={{ width: `${percent(group.total_payroll, biggest)}%` }} />
                    </div>
                  </td>
                  <td className="num">{money(group.average_salary, base)}</td>
                  <td className="num">{money(group.median_salary, base)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="footnote">
        Both the average and the median are shown because they disagree, and the gap is the
        interesting part. Every figure here is computed by the database over the filtered set, not
        by adding up a page of results.
      </p>
    </>
  );
}
