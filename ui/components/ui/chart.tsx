"use client";

import * as React from "react";
import * as RechartsPrimitive from "recharts";

const THEMES = { light: "", dark: ".dark" } as const;

export type ChartConfig = {
  [k in string]: {
    label?: React.ReactNode;
    icon?: React.ComponentType;
    color?: string;
    theme?: Record<keyof typeof THEMES, string>;
  };
};

type ChartContextProps = { config: ChartConfig };
const ChartContext = React.createContext<ChartContextProps | null>(null);

function useChart() {
  const context = React.useContext(ChartContext);
  if (!context) throw new Error("useChart must be used within a <ChartContainer />");
  return context;
}

function ChartStyle({ id, config }: { id: string; config: ChartConfig }) {
  const colorConfig = Object.entries(config).filter(([, cfg]) => cfg.theme ?? cfg.color);
  if (!colorConfig.length) return null;
  return (
    <style
      dangerouslySetInnerHTML={{
        __html: Object.entries(THEMES)
          .map(([, prefix]) =>
            [
              `${prefix} [data-chart=${id}] {`,
              ...colorConfig.map(([key, cfg]) => {
                const color = cfg.theme?.[prefix as keyof typeof THEMES] ?? cfg.color;
                return color ? `  --color-${key}: ${color};` : null;
              }),
              "}",
            ]
              .filter(Boolean)
              .join("\n")
          )
          .join("\n"),
      }}
    />
  );
}

function ChartContainer({
  id,
  className,
  children,
  config,
  ...props
}: React.ComponentProps<"div"> & {
  config: ChartConfig;
  children: React.ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>["children"];
}) {
  const uniqueId = React.useId();
  const chartId = `chart-${id ?? uniqueId.replace(/:/g, "")}`;
  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-chart={chartId}
        className={`flex aspect-video justify-center text-xs ${className ?? ""}`}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <RechartsPrimitive.ResponsiveContainer>{children}</RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  );
}

// Minimal tooltip content — typed to avoid recharts v3 strict-type issues
function ChartTooltipContent({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean;
  payload?: Array<{
    dataKey?: string | number;
    name?: string | number;
    value?: number | string;
    color?: string;
    payload?: Record<string, unknown>;
  }>;
  label?: string;
  formatter?: (
    value: unknown,
    name: unknown,
    props: { payload?: Record<string, unknown> }
  ) => React.ReactNode;
}) {
  const { config } = useChart();
  if (!active || !payload?.length) return null;

  return (
    <div className="grid min-w-[8rem] gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raise)] px-2.5 py-1.5 text-xs shadow-xl">
      {label && <p className="font-medium text-[var(--color-text-primary)]">{label}</p>}
      <div className="grid gap-1">
        {payload.map((item, i) => {
          const key = String(item.dataKey ?? item.name ?? "value");
          const cfgEntry = config[key];
          if (formatter) {
            return <div key={i}>{formatter(item.value, item.name, { payload: item.payload })}</div>;
          }
          return (
            <div key={i} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-1.5">
                {item.color && (
                  <div className="h-2 w-2 rounded-sm shrink-0" style={{ background: item.color }} />
                )}
                <span className="text-[var(--color-text-muted)]">
                  {cfgEntry?.label ?? item.name ?? key}
                </span>
              </div>
              {item.value !== undefined && (
                <span className="font-mono font-semibold tabular-nums text-[var(--color-text-primary)]">
                  {typeof item.value === "number" ? item.value.toLocaleString() : item.value}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Legend content
function ChartLegendContent({
  payload,
  className,
}: {
  payload?: Array<{ value?: string; color?: string; dataKey?: string }>;
  className?: string;
}) {
  const { config } = useChart();
  if (!payload?.length) return null;
  return (
    <div className={`flex items-center justify-center gap-4 pt-3 ${className ?? ""}`}>
      {payload.map((item, i) => {
        const key = String(item.dataKey ?? item.value ?? "");
        const cfgEntry = config[key];
        return (
          <div
            key={i}
            className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)]"
          >
            <div className="h-2 w-2 rounded-sm shrink-0" style={{ background: item.color }} />
            {cfgEntry?.label ?? item.value}
          </div>
        );
      })}
    </div>
  );
}

const ChartTooltip = RechartsPrimitive.Tooltip;
const ChartLegend = RechartsPrimitive.Legend;

export {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  ChartStyle,
};
