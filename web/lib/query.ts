/**
 * Filter state lives in the URL and nowhere else.
 *
 * That is what makes server-side pagination honest rather than decorative: page 4 of Engineering
 * in India is a real address you can bookmark, share and go back to, and the server can render it
 * without any client state to rehydrate.
 */

export type RawSearchParams = Record<string, string | string[] | undefined>;

export const FILTER_KEYS = ["country", "department", "role", "search"] as const;

export function first(params: RawSearchParams, key: string): string {
  const value = params[key];
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export function positiveInt(params: RawSearchParams, key: string, fallback: number): number {
  const parsed = Number.parseInt(first(params, key), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

/** Only the keys the API knows about, so a stray query param cannot become a 400. */
export function toApiParams(params: RawSearchParams, extra: Record<string, string> = {}) {
  const api = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = first(params, key).trim();
    if (value) api.set(key, value);
  }
  for (const [key, value] of Object.entries(extra)) {
    if (value) api.set(key, value);
  }
  return api;
}

/** A href for the same page with some params changed. Anything set to "" is dropped. */
export function withParams(params: RawSearchParams, changes: Record<string, string>): string {
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const single = Array.isArray(value) ? value[0] : value;
    if (single) next.set(key, single);
  }
  for (const [key, value] of Object.entries(changes)) {
    if (value) next.set(key, value);
    else next.delete(key);
  }
  const query = next.toString();
  return query ? `?${query}` : "?";
}
