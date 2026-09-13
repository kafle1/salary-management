import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { count } from "@/lib/format";
import { cn } from "@/lib/utils";
import { withParams, type RawSearchParams } from "@/lib/query";

const PAGE_SIZES = [25, 50, 100];

type Props = {
  params: RawSearchParams;
  page: number;
  pageSize: number;
  totalPages: number;
  total: number;
  hasNext: boolean;
  hasPrevious: boolean;
};

export function Pagination({ params, page, pageSize, totalPages, total, hasNext, hasPrevious }: Props) {
  const href = (changes: Record<string, string>) => `/employees${withParams(params, changes)}`;
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  const step = buttonVariants({ variant: "outline", size: "sm" });

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 text-sm text-muted-foreground">
      <div>
        {count(from)} to {count(to)} of {count(total)}
      </div>

      <div className="flex items-center gap-1">
        <span className="mr-1">Rows</span>
        {PAGE_SIZES.map((size) => (
          <Link
            key={size}
            href={href({ page_size: String(size), page: "" })}
            aria-current={size === pageSize ? "page" : undefined}
            className={cn(
              buttonVariants({ variant: size === pageSize ? "secondary" : "ghost", size: "sm" }),
            )}
          >
            {size}
          </Link>
        ))}
      </div>

      <div className="flex items-center gap-2">
        {hasPrevious ? (
          <Link href={href({ page: String(page - 1) })} className={step}>
            <ChevronLeftIcon />
            Previous
          </Link>
        ) : (
          <span className={cn(step, "pointer-events-none opacity-50")}>
            <ChevronLeftIcon />
            Previous
          </span>
        )}
        <span>
          Page {count(page)} of {count(Math.max(totalPages, 1))}
        </span>
        {hasNext ? (
          <Link href={href({ page: String(page + 1) })} className={step}>
            Next
            <ChevronRightIcon />
          </Link>
        ) : (
          <span className={cn(step, "pointer-events-none opacity-50")}>
            Next
            <ChevronRightIcon />
          </span>
        )}
      </div>
    </div>
  );
}
