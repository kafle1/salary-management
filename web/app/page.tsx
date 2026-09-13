import { ArrowRightIcon } from "lucide-react";
import Link from "next/link";
import { GroupChart, PayBandsChart } from "@/components/charts";
import { FilterBar } from "@/components/filter-bar";
import { ApiUnavailable, PageHeader } from "@/components/page";
import { PeerGapTable } from "@/components/peer-gap-table";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  fetchBelowPeers,
  fetchFilterOptions,
  fetchSummary,
  type DashboardSummary,
  type FilterOptions,
  type PeerGapReport,
} from "@/lib/api";
import { compactMoney, count, money, percent } from "@/lib/format";
import { first, toApiParams, withParams, type RawSearchParams } from "@/lib/query";

// filters live in the url, so every render is a fresh answer to a specific question
export const dynamic = "force-dynamic";

const GROUP_NAMES: Record<string, string> = {
  country: "country",
  department: "department",
  role: "role",
};

function Kpi({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card className="gap-1">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-xl font-semibold tabular-nums sm:text-2xl">{value}</CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{note}</CardContent>
    </Card>
  );
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<RawSearchParams>;
}) {
  const params = await searchParams;
  const groupBy = first(params, "group_by") || "country";

  let summary: DashboardSummary;
  let options: FilterOptions;
  let peers: PeerGapReport;
  try {
    [summary, options, peers] = await Promise.all([
      fetchSummary(toApiParams(params, { group_by: groupBy })),
      fetchFilterOptions(),
      fetchBelowPeers(toApiParams(params, { limit: "5" })),
    ]);
  } catch (error) {
    return <ApiUnavailable title="Payroll overview" error={error} />;
  }

  const { overall, groups, bands, base_currency: base } = summary;
  const groupName = GROUP_NAMES[summary.group_by] ?? summary.group_by;
  const biggest = groups.reduce((max, g) => Math.max(max, Number(g.total_payroll)), 0);

  return (
    <>
      <PageHeader
        title="Payroll overview"
        description={`Everyone's pay converted to ${base} with the stored exchange rates. Filters apply to the whole page.`}
      />

      <FilterBar params={params} options={options} groupBy />

      {overall.headcount === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            No one matches these filters.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Kpi label="People" value={count(overall.headcount)} note="in this selection" />
            <Kpi
              label="Payroll per year"
              value={compactMoney(overall.total_payroll, base)}
              note={money(overall.total_payroll, base)}
            />
            <Kpi
              label="Median pay"
              value={money(overall.median_salary, base)}
              note={`Average is ${money(overall.average_salary, base)}`}
            />
            <Kpi
              label="Pay range"
              value={`${compactMoney(overall.lowest_salary, base)} to ${compactMoney(overall.highest_salary, base)}`}
              note="lowest to highest paid"
            />
          </section>

          <section className="grid gap-4 lg:grid-cols-5">
            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle>Pay by {groupName}</CardTitle>
                <CardDescription>Ordered by total spend. Hover a bar for the numbers.</CardDescription>
              </CardHeader>
              <CardContent>
                <GroupChart
                  data={groups.map((g) => ({
                    label: g.label,
                    headcount: g.headcount,
                    median: Number(g.median_salary ?? 0),
                    average: Number(g.average_salary ?? 0),
                    total: Number(g.total_payroll),
                  }))}
                />
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>How pay is spread</CardTitle>
                <CardDescription>
                  People in each {bands[0] ? compactMoney(bands[0].upper, base) : ""} pay band
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PayBandsChart
                  data={bands.map((b) => ({
                    lower: Number(b.lower),
                    upper: Number(b.upper),
                    headcount: b.headcount,
                  }))}
                />
              </CardContent>
            </Card>
          </section>

          <Card className="pb-0">
            <CardHeader>
              <CardTitle>Breakdown by {groupName}</CardTitle>
              <CardDescription>
                {groups.length} groups. Mean and median both shown, because the gap between them is
                where the outliers are.
              </CardDescription>
            </CardHeader>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4 capitalize">{groupName}</TableHead>
                  <TableHead className="text-right">People</TableHead>
                  <TableHead className="text-right">Total spend</TableHead>
                  <TableHead className="w-40">Share of spend</TableHead>
                  <TableHead className="text-right">Median</TableHead>
                  <TableHead className="text-right">Average</TableHead>
                  <TableHead className="pr-4 text-right">Range</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {groups.map((group) => {
                  const share = percent(group.total_payroll, overall.total_payroll);
                  return (
                    <TableRow key={group.key}>
                      <TableCell className="pl-4 font-medium">{group.label}</TableCell>
                      <TableCell className="text-right tabular-nums">{count(group.headcount)}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {money(group.total_payroll, base)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full rounded-full bg-chart-1"
                              style={{ width: `${biggest ? (Number(group.total_payroll) / biggest) * 100 : 0}%` }}
                            />
                          </div>
                          <span className="w-10 text-right text-xs text-muted-foreground tabular-nums">
                            {share.toFixed(1)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {money(group.median_salary, base)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {money(group.average_salary, base)}
                      </TableCell>
                      <TableCell className="pr-4 text-right text-muted-foreground tabular-nums">
                        {compactMoney(group.lowest_salary, base)} to{" "}
                        {compactMoney(group.highest_salary, base)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Card>

          <Card className="pb-0">
            <CardHeader>
              <CardTitle>Paid well under their peers</CardTitle>
              <CardDescription>
                {count(peers.total)} people earn under {peers.threshold_percent}% of the median for
                the same role in the same country. Roles with fewer than {peers.min_peers} people in a
                country are left out.
              </CardDescription>
              <CardAction>
                <Link
                  href={`/pay-review${withParams(params, { group_by: "" })}`}
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                  See all
                  <ArrowRightIcon />
                </Link>
              </CardAction>
            </CardHeader>
            {peers.items.length ? (
              <PeerGapTable items={peers.items} />
            ) : (
              <CardContent className="pb-4 text-muted-foreground">
                Nobody in this selection is that far below their peers.
              </CardContent>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
