"use client";

import { useTranslations } from "next-intl";
import { Ellipsis } from "lucide-react";
import { Bar, BarChart, type BarShapeProps, XAxis, YAxis } from "recharts";

import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";

const realtimeData = [
  { minute: 1, visitors: 0 },
  { minute: 2, visitors: 6 },
  { minute: 3, visitors: 12 },
  { minute: 4, visitors: 20 },
  { minute: 5, visitors: 12 },
  { minute: 6, visitors: 0 },
  { minute: 7, visitors: 6 },
  { minute: 8, visitors: 6 },
  { minute: 9, visitors: 0 },
  { minute: 10, visitors: 4 },
  { minute: 11, visitors: 0 },
  { minute: 12, visitors: 20 },
  { minute: 13, visitors: 15 },
  { minute: 14, visitors: 4 },
  { minute: 15, visitors: 6 },
  { minute: 16, visitors: 0 },
  { minute: 17, visitors: 4 },
  { minute: 18, visitors: 12 },
  { minute: 19, visitors: 20 },
  { minute: 20, visitors: 0 },
  { minute: 21, visitors: 4 },
  { minute: 22, visitors: 20 },
  { minute: 23, visitors: 12 },
  { minute: 24, visitors: 0 },
  { minute: 25, visitors: 6 },
  { minute: 26, visitors: 6 },
  { minute: 27, visitors: 0 },
  { minute: 28, visitors: 20 },
  { minute: 29, visitors: 0 },
  { minute: 30, visitors: 4 },
];

const chartConfig = {
  visitors: {
    color: "var(--chart-3)",
    label: "بازدیدکنندگان",
  },
} satisfies ChartConfig;

function RealtimeBarShape(props: BarShapeProps) {
  const { height, payload, width, x, y } = props;
  const barPayload = payload as (typeof realtimeData)[number] | undefined;
  const barHeightValue = Number(height);
  const barWidthValue = Number(width);
  const xValue = Number(x);
  const yValue = Number(y);
  const visitors = barPayload?.visitors ?? 0;
  const fill = "var(--color-visitors)";
  const fillOpacity = visitors >= 18 ? 0.95 : 0.4;
  const baselineFill = visitors === 0 ? "var(--destructive)" : fill;
  const baselineOpacity = visitors === 0 ? 1 : fillOpacity;
  const baselineY = yValue + barHeightValue - 2;
  const barGap = 4;
  const barHeight = Math.max(0, barHeightValue - barGap);

  return (
    <g>
      <rect
        x={xValue}
        y={baselineY}
        width={barWidthValue}
        height={2}
        rx={1}
        fill={baselineFill}
        fillOpacity={baselineOpacity}
      />
      {visitors > 0 && barHeight > 0 ? (
        <rect
          x={xValue}
          y={yValue}
          width={barWidthValue}
          height={barHeight}
          rx={2}
          fill={fill}
          fillOpacity={fillOpacity}
        />
      ) : null}
    </g>
  );
}

export function RealtimeVisitors() {
  const t = useTranslations("Analytics.realtime");

  const topCountries = [
    { code: "US", name: t("countries.us"), count: 14 },
    { code: "GB", name: t("countries.gb"), count: 4 },
    { code: "CA", name: t("countries.ca"), count: 3 },
    { code: "IN", name: t("countries.in"), count: 3 },
  ];

  return (
    <Card className="h-full" dir="rtl">
      <CardHeader>
        <CardTitle className="font-normal text-right">{t("title")}</CardTitle>
        <CardAction>
          <Ellipsis className="size-4" />
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        <div className="flex items-end justify-between">
          <div className="flex items-baseline gap-1" dir="rtl">
            <span className="text-2xl font-semibold leading-none tracking-tight">۲۴</span>
            <span className="text-muted-foreground text-sm pr-1">{t("visitors_per_minute")}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-green-500 opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-green-500" />
            </span>
            <span>{t("live")}</span>
          </div>
        </div>

        <ChartContainer config={chartConfig} className="h-36 w-full">
          <BarChart data={realtimeData} margin={{ bottom: 0, left: 0, right: 0, top: 0 }} barCategoryGap={3}>
            <XAxis dataKey="minute" hide />
            <YAxis hide domain={[0, 22]} />
            <ChartTooltip cursor={false} content={<ChartTooltipContent hideLabel />} />
            <Bar dataKey="visitors" fill="var(--color-visitors)" shape={RealtimeBarShape} />
          </BarChart>
        </ChartContainer>

        <div className="grid grid-cols-2 text-right">
          {topCountries.map((country, index) => (
            <div 
              key={country.code}
              className={`
                flex items-center gap-3 
                ${index < 2 ? 'border-border/50 border-b' : 'pt-4 pb-1'} 
                ${index % 2 === 0 ? 'border-border/50 border-l pl-5 pb-4' : 'pr-5 pb-4'} 
                ${index >= 2 ? 'pt-4' : ''}
                justify-start
              `}
            >
              <span aria-hidden="true" className={`flag:${country.code} shrink-0 rounded-xs text-lg ring-1 ring-foreground/10`} />
              <span className="min-w-0 flex-1 truncate text-sm">{country.name}</span>
              <span className="text-sm font-medium" dir="ltr">{country.count}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}