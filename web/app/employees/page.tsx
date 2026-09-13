import Link from "next/link";
import { AddEmployeeButton, EmployeeEditor, EmployeeRowMenu } from "@/components/employee-editor";
import { FilterBar } from "@/components/filter-bar";
import { ApiUnavailable, PageHeader } from "@/components/page";
import { Pagination } from "@/components/pagination";
import { SortHeader } from "@/components/sort-header";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  fetchCountries,
  fetchEmployees,
  fetchFilterOptions,
  type EmployeePage,
  type FilterOptions,
  type PayableCountry,
} from "@/lib/api";
import { count, hireDate, money } from "@/lib/format";
import { first, positiveInt, toApiParams, type RawSearchParams } from "@/lib/query";

export const dynamic = "force-dynamic";

export default async function EmployeesPage({
  searchParams,
}: {
  searchParams: Promise<RawSearchParams>;
}) {
  const params = await searchParams;
  const page = positiveInt(params, "page", 1);
  const pageSize = positiveInt(params, "page_size", 25);

  const apiParams = toApiParams(params, {
    page: String(page),
    page_size: String(pageSize),
    sort_by: first(params, "sort_by"),
    sort_dir: first(params, "sort_dir"),
  });

  let result: EmployeePage;
  let options: FilterOptions;
  let countries: PayableCountry[];
  try {
    [result, options, countries] = await Promise.all([
      fetchEmployees(apiParams),
      fetchFilterOptions(),
      fetchCountries(),
    ]);
  } catch (error) {
    return <ApiUnavailable title="Employees" error={error} />;
  }

  return (
    <EmployeeEditor countries={countries} options={options}>
      <PageHeader
        title="Employees"
        description={`${count(result.total)} people. Pay is stored in each person's own currency and shown in USD.`}
        action={<AddEmployeeButton />}
      />

      <FilterBar params={params} options={options} />

      <Card className="gap-0 py-0">
        <Table>
          <TableHeader>
            <TableRow>
              <SortHeader params={params} field="name" label="Name" className="pl-4" />
              <SortHeader params={params} field="country" label="Country" />
              <SortHeader params={params} field="department" label="Department" />
              <SortHeader params={params} field="role" label="Role" />
              <SortHeader params={params} field="hire_date" label="Hired" />
              <SortHeader params={params} field="salary_usd" label="Salary (USD)" numeric />
              <TableHead className="w-12">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.items.map((employee) => (
              <TableRow key={employee.id}>
                <TableCell className="pl-4">
                  <Link href={`/employees/${employee.id}`} className="font-medium hover:underline">
                    {employee.full_name}
                  </Link>
                  <div className="text-xs text-muted-foreground">{employee.email}</div>
                </TableCell>
                <TableCell>{employee.country_name}</TableCell>
                <TableCell>{employee.department}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{employee.role}</Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{hireDate(employee.hire_date)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  <div>{money(employee.salary_in_base.amount, employee.salary_in_base.currency)}</div>
                  {employee.salary.currency === employee.salary_in_base.currency ? null : (
                    <div className="text-xs text-muted-foreground">
                      paid {money(employee.salary.amount, employee.salary.currency)}
                    </div>
                  )}
                </TableCell>
                <TableCell className="pr-4 text-right">
                  <EmployeeRowMenu employee={employee} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {result.items.length === 0 ? (
          <p className="py-10 text-center text-muted-foreground">No one matches these filters.</p>
        ) : null}

        <Pagination
          params={params}
          page={result.page}
          pageSize={result.page_size}
          totalPages={result.total_pages}
          total={result.total}
          hasNext={result.has_next}
          hasPrevious={result.has_previous}
        />
      </Card>
    </EmployeeEditor>
  );
}
