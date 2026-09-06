import Link from "next/link";
import { count } from "@/lib/format";
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

export function Pagination({
  params,
  page,
  pageSize,
  totalPages,
  total,
  hasNext,
  hasPrevious,
}: Props) {
  const href = (changes: Record<string, string>) => `/employees${withParams(params, changes)}`;
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="pager">
      <div>
        {count(from)}&ndash;{count(to)} of {count(total)}
      </div>

      <div className="sizes">
        <span>Rows</span>
        {PAGE_SIZES.map((size) => (
          <Link
            key={size}
            href={href({ page_size: String(size), page: "" })}
            aria-current={size === pageSize ? "true" : undefined}
          >
            {size}
          </Link>
        ))}
      </div>

      <div className="steps">
        {hasPrevious ? (
          <Link href={href({ page: String(page - 1) })}>Previous</Link>
        ) : (
          <span className="disabled">Previous</span>
        )}
        <span>
          Page {count(page)} of {count(Math.max(totalPages, 1))}
        </span>
        {hasNext ? (
          <Link href={href({ page: String(page + 1) })}>Next</Link>
        ) : (
          <span className="disabled">Next</span>
        )}
      </div>
    </div>
  );
}
