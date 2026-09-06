import Link from "next/link";
import { first, withParams, type RawSearchParams } from "@/lib/query";

type Props = {
  params: RawSearchParams;
  field: string;
  label: string;
  numeric?: boolean;
};

/** A sort is a link, not a click handler, so the sorted view has its own address. */
export function SortHeader({ params, field, label, numeric }: Props) {
  const active = (first(params, "sort_by") || "name") === field;
  const direction = first(params, "sort_dir") || "asc";
  const next = active && direction === "asc" ? "desc" : "asc";

  return (
    <th className={numeric ? "num" : undefined}>
      <Link
        href={`/employees${withParams(params, { sort_by: field, sort_dir: next, page: "" })}`}
        className={active ? "sorted" : undefined}
      >
        {label}
        {active ? <span aria-hidden>{direction === "asc" ? "↑" : "↓"}</span> : null}
      </Link>
    </th>
  );
}
