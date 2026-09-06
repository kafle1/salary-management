/**
 * Every page renders on the server and talks to the API from there, so the browser never sees
 * the API host and there is no CORS round trip on the happy path. It also means the 10,000 rows
 * stay where they are: the page asks for one slice and one set of aggregates.
 */

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export type Money = { amount: string; currency: string };

export type Employee = {
  id: number;
  full_name: string;
  email: string;
  country_code: string;
  country_name: string;
  department: string;
  role: string;
  hire_date: string;
  salary: Money;
  salary_in_base: Money;
};

export type EmployeePage = {
  items: Employee[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
};

export type SalaryStats = {
  headcount: number;
  total_payroll: string;
  average_salary: string | null;
  median_salary: string | null;
};

export type GroupStats = SalaryStats & { key: string; label: string };

export type DashboardSummary = {
  base_currency: string;
  group_by: string;
  overall: SalaryStats;
  groups: GroupStats[];
};

export type FilterOptions = {
  countries: { code: string; name: string }[];
  departments: string[];
  roles: string[];
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function getJson<T>(path: string, params: URLSearchParams): Promise<T> {
  const query = params.toString();
  const response = await fetch(`${API_BASE_URL}${path}${query ? `?${query}` : ""}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || response.statusText);
  }
  return (await response.json()) as T;
}

export function fetchEmployees(params: URLSearchParams): Promise<EmployeePage> {
  return getJson<EmployeePage>("/employees", params);
}

export function fetchFilterOptions(): Promise<FilterOptions> {
  return getJson<FilterOptions>("/employees/filter-options", new URLSearchParams());
}

export function fetchSummary(params: URLSearchParams): Promise<DashboardSummary> {
  return getJson<DashboardSummary>("/dashboard/summary", params);
}
