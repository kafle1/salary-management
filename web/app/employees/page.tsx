import { FilterBar } from "@/components/filter-bar";
import { Pagination } from "@/components/pagination";
import { SortHeader } from "@/components/sort-header";
import {
  describeError,
  fetchEmployees,
  fetchFilterOptions,
  type EmployeePage,
  type FilterOptions,
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
  try {
    [result, options] = await Promise.all([fetchEmployees(apiParams), fetchFilterOptions()]);
  } catch (error) {
    return (
      <>
        <h1>Employees</h1>
        <p className="error">
          Could not load this view. If nothing is running, start the stack with{" "}
          <code>docker compose up</code>. ({describeError(error)})
        </p>
      </>
    );
  }

  return (
    <>
      <h1>Employees</h1>
      <p className="lede">
        {count(result.total)} people. One page is fetched at a time, sorted and filtered by the
        database.
      </p>

      <FilterBar basePath="/employees" params={params} options={options} />

      <div className="panel">
        <table>
          <thead>
            <tr>
              <SortHeader params={params} field="name" label="Name" />
              <SortHeader params={params} field="country" label="Country" />
              <SortHeader params={params} field="department" label="Department" />
              <SortHeader params={params} field="role" label="Role" />
              <SortHeader params={params} field="hire_date" label="Hired" />
              <SortHeader params={params} field="salary_usd" label="Salary (USD)" numeric />
            </tr>
          </thead>
          <tbody>
            {result.items.map((employee) => (
              <tr key={employee.id}>
                <td>
                  <div className="name">{employee.full_name}</div>
                  <div className="sub">{employee.email}</div>
                </td>
                <td>{employee.country_name}</td>
                <td>{employee.department}</td>
                <td>
                  <span className="tag">{employee.role}</span>
                </td>
                <td className="sub">{hireDate(employee.hire_date)}</td>
                <td className="num">
                  <div>{money(employee.salary_in_base.amount, employee.salary_in_base.currency)}</div>
                  {employee.salary.currency === employee.salary_in_base.currency ? null : (
                    <div className="native">
                      paid {money(employee.salary.amount, employee.salary.currency)}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {result.items.length === 0 ? <p className="empty">No one matches these filters.</p> : null}

        <Pagination
          params={params}
          page={result.page}
          pageSize={result.page_size}
          totalPages={result.total_pages}
          total={result.total}
          hasNext={result.has_next}
          hasPrevious={result.has_previous}
        />
      </div>

      <p className="footnote">
        Salaries are stored in the currency each person is actually paid in. The USD column is the
        stored amount joined to the seeded rate table inside the query, which is why sorting by pay
        works across currencies without loading the table.
      </p>
    </>
  );
}
