"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart";

// charts get plain numbers, parsed from the API's money strings on the server, for drawing only

const usd = (value: number, compact = false) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 0,
  }).format(value);

function Tip({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-medium">{title}</div>
      {lines.map((line) => (
        <div key={line} className="text-muted-foreground">
          {line}
        </div>
      ))}
    </div>
  );
}

export type GroupPoint = {
  label: string;
  headcount: number;
  median: number;
  average: number;
  total: number;
};

const MEASURES = [
  { key: "median", label: "Median" },
  { key: "average", label: "Average" },
  { key: "total", label: "Total spend" },
] as const;

export function GroupChart({ data }: { data: GroupPoint[] }) {
  const [measure, setMeasure] = useState<(typeof MEASURES)[number]["key"]>("median");
  const config = { [measure]: { label: measure, color: "var(--chart-1)" } } satisfies ChartConfig;

  return (
    <div>
      <div className="mb-3 flex gap-1" role="group" aria-label="Measure">
        {MEASURES.map((option) => (
          <Button
            key={option.key}
            size="sm"
            variant={measure === option.key ? "secondary" : "ghost"}
            aria-pressed={measure === option.key}
            onClick={() => setMeasure(option.key)}
          >
            {option.label}
          </Button>
        ))}
      </div>
      <ChartContainer
        config={config}
        className="aspect-auto w-full"
        style={{ height: Math.max(160, data.length * 36 + 24) }}
      >
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid horizontal={false} />
          <YAxis
            dataKey="label"
            type="category"
            width={130}
            tickLine={false}
            axisLine={false}
            interval={0}
          />
          <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={(v) => usd(v, true)} />
          <ChartTooltip
            cursor={{ fillOpacity: 0.4 }}
            content={({ active, payload }) => {
              const point = active ? (payload?.[0]?.payload as GroupPoint | undefined) : undefined;
              if (!point) return null;
              return (
                <Tip
                  title={point.label}
                  lines={[
                    `${point.headcount.toLocaleString("en-US")} people`,
                    `Median ${usd(point.median)}`,
                    `Average ${usd(point.average)}`,
                    `Total ${usd(point.total, true)}`,
                  ]}
                />
              );
            }}
          />
          <Bar dataKey={measure} fill={`var(--color-${measure})`} radius={4} />
        </BarChart>
      </ChartContainer>
    </div>
  );
}

export type BandPoint = { lower: number; upper: number; headcount: number };

export function PayBandsChart({ data }: { data: BandPoint[] }) {
  const config = { headcount: { label: "People", color: "var(--chart-1)" } } satisfies ChartConfig;
  const points = data.map((band) => ({ ...band, label: usd(band.lower, true) }));

  return (
    <ChartContainer config={config} className="aspect-auto h-80 w-full">
      <BarChart data={points} margin={{ left: 0, right: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="label" tickLine={false} axisLine={false} interval={0} />
        <YAxis tickLine={false} axisLine={false} width={44} allowDecimals={false} />
        <ChartTooltip
          cursor={{ fillOpacity: 0.4 }}
          content={({ active, payload }) => {
            const band = active ? (payload?.[0]?.payload as BandPoint | undefined) : undefined;
            if (!band) return null;
            return (
              <Tip
                title={`${usd(band.lower)} up to ${usd(band.upper)}`}
                lines={[`${band.headcount.toLocaleString("en-US")} people`]}
              />
            );
          }}
        />
        <Bar dataKey="headcount" fill="var(--color-headcount)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartContainer>
  );
}
