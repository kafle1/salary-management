/**
 * Money arrives as a fixed two-place string so nothing is lost in transit. It is parsed here, at
 * the last possible moment, and only for display.
 */

export function money(amount: string | null, currency: string, fractionDigits = 0): string {
  if (amount === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(Number(amount));
}

export function compactMoney(amount: string | null, currency: string): string {
  if (amount === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    notation: "compact",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(Number(amount));
}

export function count(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function percent(part: string, whole: string): number {
  const total = Number(whole);
  if (!total) return 0;
  return (Number(part) / total) * 100;
}

export function hireDate(value: string): string {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** "4 yr 2 mo" from a hire date, measured against today in UTC. */
export function tenure(value: string, now = new Date()): string {
  const hired = new Date(`${value}T00:00:00Z`);
  let months =
    (now.getUTCFullYear() - hired.getUTCFullYear()) * 12 + now.getUTCMonth() - hired.getUTCMonth();
  if (now.getUTCDate() < hired.getUTCDate()) months -= 1;
  if (months < 1) return "under a month";
  const years = Math.floor(months / 12);
  const rest = months % 12;
  return [years ? `${years} yr` : "", rest ? `${rest} mo` : ""].filter(Boolean).join(" ");
}
