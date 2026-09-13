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

export type SalaryChange = {
  changed_on: string;
  previous: Money | null;
  new: Money;
  note: string | null;
};

export type EmployeeDetail = Employee & { history: SalaryChange[] };

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
  lowest_salary: string | null;
  highest_salary: string | null;
};

export type GroupStats = SalaryStats & { key: string; label: string };

export type PayBand = { lower: string; upper: string; headcount: number };

export type DashboardSummary = {
  base_currency: string;
  group_by: string;
  overall: SalaryStats;
  groups: GroupStats[];
  bands: PayBand[];
};

export type PeerGap = {
  employee: Employee;
  peer_median: Money;
  peers: number;
  percent_of_median: number;
};

export type PeerGapReport = {
  threshold_percent: number;
  min_peers: number;
  total: number;
  items: PeerGap[];
};

export type FilterOptions = {
  countries: { code: string; name: string }[];
  departments: string[];
  roles: string[];
};

export type PayableCountry = { code: string; name: string; currency: string };

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function getJson<T>(path: string, params = new URLSearchParams()): Promise<T> {
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

export function fetchEmployee(id: number): Promise<EmployeeDetail> {
  return getJson<EmployeeDetail>(`/employees/${id}`);
}

export function fetchFilterOptions(): Promise<FilterOptions> {
  return getJson<FilterOptions>("/employees/filter-options");
}

export function fetchCountries(): Promise<PayableCountry[]> {
  return getJson<PayableCountry[]>("/countries");
}

export function fetchSummary(params: URLSearchParams): Promise<DashboardSummary> {
  return getJson<DashboardSummary>("/dashboard/summary", params);
}

export function fetchBelowPeers(params: URLSearchParams): Promise<PeerGapReport> {
  return getJson<PeerGapReport>("/dashboard/below-peers", params);
}

export type WriteResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; detail: string; errors: Record<string, string> };

/** Writes hand back the API's field errors instead of throwing, so a form can show them. */
export async function sendJson<T>(
  method: "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown,
): Promise<WriteResult<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (response.ok) {
    const data = response.status === 204 ? null : await response.json();
    return { ok: true, data: data as T };
  }
  const payload = await response.json().catch(() => ({}));
  return {
    ok: false,
    status: response.status,
    detail: typeof payload.detail === "string" ? payload.detail : response.statusText,
    errors: payload.errors ?? {},
  };
}

/** A 422 from a hand-edited url and a dead API are different problems, so say which. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) return `${error.status} ${error.message.slice(0, 200)}`;
  return error instanceof Error ? error.message : String(error);
}
