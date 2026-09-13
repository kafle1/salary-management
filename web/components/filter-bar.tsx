"use client";

import { SearchIcon, XIcon } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { FilterOptions } from "@/lib/api";
import { first, FILTER_KEYS, withParams, type RawSearchParams } from "@/lib/query";

const GROUPINGS = [
  { value: "country", label: "By country" },
  { value: "department", label: "By department" },
  { value: "role", label: "By role" },
];

type Item = { value: string | null; label: string };

function FilterSelect({
  label,
  value,
  items,
  onChange,
}: {
  label: string;
  value: string | null;
  items: Item[];
  onChange: (value: string) => void;
}) {
  return (
    <Select items={items} value={value} onValueChange={(next) => onChange(next ?? "")}>
      <SelectTrigger aria-label={label} className="w-full bg-background sm:w-44">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {items.map((item) => (
          <SelectItem key={item.value ?? "all"} value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

type Props = {
  params: RawSearchParams;
  options: FilterOptions;
  groupBy?: boolean;
};

export function FilterBar({ params, options, groupBy }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const search = first(params, "search");
  const filtered = FILTER_KEYS.some((key) => first(params, key));

  // any change resets to page 1, otherwise you land on page 7 of a 2 page result
  const go = (changes: Record<string, string>) =>
    router.push(`${pathname}${withParams(params, { ...changes, page: "" })}`);

  return (
    <form
      className="mb-6 flex flex-wrap items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        const typed = new FormData(event.currentTarget).get("search");
        go({ search: typeof typed === "string" ? typed.trim() : "" });
      }}
    >
      <div className="relative w-full sm:w-64">
        <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          name="search"
          aria-label="Search by name or email"
          // uncontrolled and keyed on the url, so Clear actually empties the box
          key={search}
          defaultValue={search}
          placeholder="Name or email, then Enter"
          className="bg-background pl-8"
        />
      </div>

      <FilterSelect
        label="Country"
        value={first(params, "country") || null}
        onChange={(country) => go({ country })}
        items={[
          { value: null, label: "All countries" },
          ...options.countries.map((c) => ({ value: c.code, label: c.name })),
        ]}
      />
      <FilterSelect
        label="Department"
        value={first(params, "department") || null}
        onChange={(department) => go({ department })}
        items={[
          { value: null, label: "All departments" },
          ...options.departments.map((d) => ({ value: d, label: d })),
        ]}
      />
      <FilterSelect
        label="Role"
        value={first(params, "role") || null}
        onChange={(role) => go({ role })}
        items={[{ value: null, label: "All roles" }, ...options.roles.map((r) => ({ value: r, label: r }))]}
      />

      {groupBy ? (
        <FilterSelect
          label="Break down by"
          value={first(params, "group_by") || "country"}
          onChange={(group_by) => go({ group_by })}
          items={GROUPINGS}
        />
      ) : null}

      {filtered ? (
        <Button
          type="button"
          variant="ghost"
          onClick={() =>
            go(Object.fromEntries(FILTER_KEYS.map((key) => [key, ""])) as Record<string, string>)
          }
        >
          <XIcon />
          Clear filters
        </Button>
      ) : null}
    </form>
  );
}
