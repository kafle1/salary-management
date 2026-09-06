"use client";

import { useRouter } from "next/navigation";
import { first, withParams, type RawSearchParams } from "@/lib/query";

const DIMENSIONS = [
  { value: "country", label: "Country" },
  { value: "department", label: "Department" },
  { value: "role", label: "Role" },
];

export function GroupBySelect({ params }: { params: RawSearchParams }) {
  const router = useRouter();
  const current = first(params, "group_by") || "country";

  return (
    <div className="field">
      <label htmlFor="group_by">Break down by</label>
      <select
        id="group_by"
        value={current}
        onChange={(event) => router.push(`/${withParams(params, { group_by: event.target.value })}`)}
      >
        {DIMENSIONS.map((dimension) => (
          <option key={dimension.value} value={dimension.value}>
            {dimension.label}
          </option>
        ))}
      </select>
    </div>
  );
}
