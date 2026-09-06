"use client";

import { useRouter } from "next/navigation";
import type { FilterOptions } from "@/lib/api";
import { first, withParams, type RawSearchParams } from "@/lib/query";

type Props = {
  basePath: string;
  params: RawSearchParams;
  options: FilterOptions;
  children?: React.ReactNode;
};

export function FilterBar({ basePath, params, options, children }: Props) {
  const router = useRouter();
  const search = first(params, "search");

  // any change resets to page 1, otherwise you land on page 7 of a 2 page result
  const go = (changes: Record<string, string>) =>
    router.push(`${basePath}${withParams(params, { ...changes, page: "" })}`);

  return (
    <form
      className="filters"
      onSubmit={(event) => {
        event.preventDefault();
        const typed = new FormData(event.currentTarget).get("search");
        go({ search: typeof typed === "string" ? typed.trim() : "" });
      }}
    >
      <div className="field">
        <label htmlFor="country">Country</label>
        <select
          id="country"
          value={first(params, "country")}
          onChange={(event) => go({ country: event.target.value })}
        >
          <option value="">All countries</option>
          {options.countries.map((country) => (
            <option key={country.code} value={country.code}>
              {country.name}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="department">Department</label>
        <select
          id="department"
          value={first(params, "department")}
          onChange={(event) => go({ department: event.target.value })}
        >
          <option value="">All departments</option>
          {options.departments.map((department) => (
            <option key={department} value={department}>
              {department}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="role">Role</label>
        <select
          id="role"
          value={first(params, "role")}
          onChange={(event) => go({ role: event.target.value })}
        >
          <option value="">All roles</option>
          {options.roles.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="search">Name or email</label>
        <input
          id="search"
          name="search"
          // uncontrolled and keyed on the url, so Reset actually empties the box
          key={search}
          defaultValue={search}
          placeholder="Search and press enter"
        />
      </div>

      {children}

      <button type="button" onClick={() => router.push(basePath)}>
        Reset
      </button>
    </form>
  );
}
