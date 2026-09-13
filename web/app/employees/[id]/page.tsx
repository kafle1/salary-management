import { ArrowLeftIcon } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { EmployeeActions, EmployeeEditor } from "@/components/employee-editor";
import { ApiUnavailable, PageHeader } from "@/components/page";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  ApiError,
  fetchCountries,
  fetchEmployee,
  fetchFilterOptions,
  fetchSummary,
  type DashboardSummary,
  type EmployeeDetail,
  type FilterOptions,
  type PayableCountry,
} from "@/lib/api";
import { count, hireDate, money, tenure } from "@/lib/format";

export const dynamic = "force-dynamic";

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-medium">{children}</dd>
    </div>
  );
}

function changePercent(previous: string, next: string): number | null {
  const before = Number(previous);
  return before ? ((Number(next) - before) / before) * 100 : null;
}

export default async function EmployeeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: raw } = await params;
  const id = Number(raw);
  if (!Number.isSafeInteger(id) || id < 1) notFound();

  let employee: EmployeeDetail;
  let options: FilterOptions;
  let countries: PayableCountry[];
  try {
    [employee, options, countries] = await Promise.all([
      fetchEmployee(id),
      fetchFilterOptions(),
      fetchCountries(),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    return <ApiUnavailable title="Employee" error={error} />;
  }

  // peers are the same role in the same country, the same comparison the pay review uses
  let peers: DashboardSummary | null = null;
  try {
    peers = await fetchSummary(
      new URLSearchParams({ country: employee.country_code, role: employee.role, group_by: "role" }),
    );
  } catch {
    peers = null;
  }

  const base = employee.salary_in_base.currency;
  const median = peers?.overall.median_salary ?? null;
  const ofMedian = median ? (Number(employee.salary_in_base.amount) / Number(median)) * 100 : null;
  const paidInBase = employee.salary.currency === base;

  return (
    <EmployeeEditor countries={countries} options={options}>
      <Link href="/employees" className={buttonVariants({ variant: "ghost", size: "sm", className: "-ml-2 mb-2" })}>
        <ArrowLeftIcon />
        Employees
      </Link>

      <PageHeader
        title={employee.full_name}
        description={`${employee.role}, ${employee.department}, ${employee.country_name}`}
        action={<EmployeeActions employee={employee} />}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Current salary</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums">
              {money(employee.salary.amount, employee.salary.currency, 2)}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {paidInBase
              ? "per year"
              : `per year, about ${money(employee.salary_in_base.amount, base)} at the stored rate`}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardDescription>Against their peers</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums">
              {ofMedian === null ? "--" : `${Math.round(ofMedian)}% of median`}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {peers && median
              ? `${employee.role} in ${employee.country_name}: ${count(peers.overall.headcount)} people, median ${money(median, base)}`
              : "Couldn't load the peer numbers."}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div className="col-span-2">
                <Fact label="Email">
                  <span className="break-all">{employee.email}</span>
                </Fact>
              </div>
              <Fact label="Hired">{hireDate(employee.hire_date)}</Fact>
              <Fact label="With the company">{tenure(employee.hire_date)}</Fact>
            </dl>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4 pb-0">
        <CardHeader>
          <CardTitle>Salary history</CardTitle>
          <CardDescription>Newest first. Every change is kept.</CardDescription>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="pl-4">Date</TableHead>
              <TableHead className="text-right">From</TableHead>
              <TableHead className="text-right">To</TableHead>
              <TableHead className="text-right">Change</TableHead>
              <TableHead className="pr-4">Note</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {employee.history.map((change, index) => {
              const delta = change.previous ? changePercent(change.previous.amount, change.new.amount) : null;
              return (
                <TableRow key={`${change.changed_on}-${index}`}>
                  <TableCell className="pl-4">{hireDate(change.changed_on)}</TableCell>
                  <TableCell className="text-right text-muted-foreground tabular-nums">
                    {change.previous ? money(change.previous.amount, change.previous.currency) : "--"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {money(change.new.amount, change.new.currency)}
                  </TableCell>
                  <TableCell className="text-right">
                    {change.previous === null ? (
                      <Badge variant="outline">Starting pay</Badge>
                    ) : delta === null || change.previous.currency !== change.new.currency ? (
                      <Badge variant="outline">New currency</Badge>
                    ) : (
                      <Badge variant={delta < 0 ? "destructive" : "secondary"}>
                        {delta > 0 ? "+" : ""}
                        {delta.toFixed(1)}%
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="pr-4 text-muted-foreground">{change.note ?? ""}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {employee.history.length === 0 ? (
          <p className="py-8 text-center text-muted-foreground">No salary changes recorded.</p>
        ) : null}
      </Card>
    </EmployeeEditor>
  );
}
