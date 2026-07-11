"use client";

import { useTranslations } from "next-intl";
import { Ellipsis } from "lucide-react";
import { Bar, BarChart, CartesianGrid, LabelList, type LabelProps, XAxis, YAxis } from "recharts";

import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const chartConfig = {
  visitors: {
    color: "var(--chart-1)",
    label: "بازدیدکنندگان",
  },
} satisfies ChartConfig;

type TrafficSourceDatum = {
  label: string;
  source: string;
  visitors: number;
};

function renderValueLabel(props: LabelProps) {
  const { height, value, y } = props;

  return (
    <text
      className="fill-foreground font-medium"
      dominantBaseline="middle"
      dx={6}
      fontSize={13}
      textAnchor="start"
      x="0%"
      y={Number(y) + Number(height) / 2}
    >
      {value}
    </text>
  );
}

function TrafficSourceBarChart({ data }: { data: TrafficSourceDatum[] }) {
  return (
    <ChartContainer config={chartConfig} className="h-64 w-full">
      <BarChart
        accessibilityLayer
        data={data}
        layout="vertical"
        margin={{
          left: 48,
          right: 0,
        }}
      >
        <CartesianGrid horizontal={false} vertical={false} />
        <YAxis dataKey="source" hide tickLine={false} type="category" />
        <XAxis dataKey="visitors" hide type="number" />
        <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="line" />} />
        <Bar barSize={40} dataKey="visitors" fill="var(--color-visitors)" fillOpacity={0.5} radius={8}>
          <LabelList className="fill-foreground font-normal text-right" dataKey="source" fontSize={13} offset={12} position="insideRight" />
          <LabelList content={renderValueLabel} dataKey="label" />
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}

export function TopTrafficSources() {
  const t = useTranslations("Analytics.traffic");

  const sourcesData: TrafficSourceDatum[] = [
    { label: "۸۹.۴k", source: t("sources.organic"), visitors: 89_400 },
    { label: "۵۵.۲k", source: t("sources.direct"), visitors: 55_200 },
    { label: "۳۸.۱k", source: t("sources.social"), visitors: 38_100 },
    { label: "۳۰.۴k", source: t("sources.referral"), visitors: 30_400 },
    { label: "۲۲.۷k", source: t("sources.paid"), visitors: 22_700 },
  ];

  const campaignsData: TrafficSourceDatum[] = [
    { label: "۱۶.۸k", source: t("campaigns.spring"), visitors: 16_800 },
    { label: "۱۲.۰k", source: t("campaigns.email"), visitors: 12_000 },
    { label: "۷.۷k", source: t("campaigns.retargeting"), visitors: 7700 },
    { label: "۵.۹k", source: t("campaigns.brand"), visitors: 5900 },
    { label: "۴.۳k", source: t("campaigns.partners"), visitors: 4300 },
  ];

  const referrersData: TrafficSourceDatum[] = [
    { label: "۱۸.۴k", source: "Google", visitors: 18_400 },
    { label: "۸.۹k", source: "LinkedIn", visitors: 8900 },
    { label: "۵.۷k", source: "Product Hunt", visitors: 5700 },
    { label: "۴.۸k", source: "GitHub", visitors: 4800 },
    { label: "۳.۶k", source: "Medium", visitors: 3600 },
  ];

  return (
    <Card className="h-full gap-2" dir="rtl">
      <CardHeader>
        <CardTitle className="font-normal text-right">{t("title")}</CardTitle>
        <CardAction>
          <Ellipsis className="size-4" />
        </CardAction>
      </CardHeader>

      <CardContent className="px-0">
        <Tabs defaultValue="sources" className="flex flex-col gap-3">
          <TabsList className="w-full justify-start border-b px-2.5 flex-row-reverse" variant="line">
            <TabsTrigger className="flex-none font-normal" value="sources">
              {t("tabs.sources")}
            </TabsTrigger>
            <TabsTrigger className="flex-none font-normal" value="campaigns">
              {t("tabs.campaigns")}
            </TabsTrigger>
            <TabsTrigger className="flex-none font-normal" value="referrers">
              {t("tabs.referrers")}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="sources" className="px-4">
            <TrafficSourceBarChart data={sourcesData} />
          </TabsContent>

          <TabsContent value="campaigns" className="px-4">
            <TrafficSourceBarChart data={campaignsData} />
          </TabsContent>

          <TabsContent value="referrers" className="px-4">
            <TrafficSourceBarChart data={referrersData} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}