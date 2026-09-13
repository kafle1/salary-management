import { ArrowDownIcon, ArrowUpIcon } from "lucide-react";
import Link from "next/link";
import { TableHead } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { first, withParams, type RawSearchParams } from "@/lib/query";

type Props = {
  params: RawSearchParams;
  field: string;
  label: string;
  numeric?: boolean;
  className?: string;
};

/** A sort is a link, not a click handler, so the sorted view has its own address. */
export function SortHeader({ params, field, label, numeric, className }: Props) {
  const active = (first(params, "sort_by") || "name") === field;
  const direction = first(params, "sort_dir") || "asc";
  const next = active && direction === "asc" ? "desc" : "asc";
  const Arrow = direction === "asc" ? ArrowUpIcon : ArrowDownIcon;

  return (
    <TableHead
      className={cn(numeric && "text-right", className)}
      aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : undefined}
    >
      <Link
        href={`/employees${withParams(params, { sort_by: field, sort_dir: next, page: "" })}`}
        className={cn(
          "inline-flex items-center gap-1 hover:text-foreground",
          active ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {label}
        {active ? <Arrow className="size-3.5" aria-hidden /> : null}
      </Link>
    </TableHead>
  );
}
