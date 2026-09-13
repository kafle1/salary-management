import { FilterBar } from "@/components/filter-bar";
import { ApiUnavailable, PageHeader } from "@/components/page";
import { PeerGapTable } from "@/components/peer-gap-table";
import { Card } from "@/components/ui/card";
import { fetchBelowPeers, fetchFilterOptions, type FilterOptions, type PeerGapReport } from "@/lib/api";
import { count } from "@/lib/format";
import { toApiParams, type RawSearchParams } from "@/lib/query";

export const dynamic = "force-dynamic";

const LIMIT = 100;

export default async function PayReviewPage({
  searchParams,
}: {
  searchParams: Promise<RawSearchParams>;
}) {
  const params = await searchParams;

  let report: PeerGapReport;
  let options: FilterOptions;
  try {
    [report, options] = await Promise.all([
      fetchBelowPeers(toApiParams(params, { limit: String(LIMIT) })),
      fetchFilterOptions(),
    ]);
  } catch (error) {
    return <ApiUnavailable title="Pay review" error={error} />;
  }

  const shown = report.items.length;

  return (
    <>
      <PageHeader
        title="Pay review"
        description={`People paid under ${report.threshold_percent}% of the median for their role in their country, furthest below first. Groups with fewer than ${report.min_peers} people are skipped, since a median of three isn't a fair bar.`}
      />

      <FilterBar params={params} options={options} />

      <Card className="gap-0 py-0">
        <div className="border-b px-4 py-3 text-sm text-muted-foreground">
          {report.total === 0
            ? "Nobody in this selection is that far below their peers."
            : shown < report.total
              ? `${count(report.total)} people. Showing the ${count(shown)} furthest below. Narrow the filters to see the rest.`
              : `${count(report.total)} people.`}
        </div>
        {shown ? <PeerGapTable items={report.items} /> : null}
      </Card>
    </>
  );
}
