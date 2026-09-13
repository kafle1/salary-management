import { describeError } from "@/lib/api";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function ApiUnavailable({ title, error }: { title: string; error: unknown }) {
  return (
    <>
      <PageHeader title={title} />
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm">
        <p className="font-medium">This page couldn&apos;t load its data.</p>
        <p className="mt-1 text-muted-foreground">
          If nothing is running, start the stack with <code>docker compose up</code>.
        </p>
        <p className="mt-2 font-mono text-xs text-muted-foreground">{describeError(error)}</p>
      </div>
    </>
  );
}
