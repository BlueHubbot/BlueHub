"use client";

import { useTranslations } from "next-intl";
import { ArrowDownRight, ArrowUpRight, Ellipsis } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";

export function AnalyticsKpiStrip() {
  const t = useTranslations("Analytics.kpis");

  const kpis = [
    {
      key: "unique_users",
      value: "213.1k",
      change: "+2.8%",
      trend: "up",
      compare: "207.3k",
      period: t("period")
    },
    {
      key: "sessions",
      value: "248.6k",
      change: "+2.1%",
      trend: "up",
      compare: "243.5k",
      period: t("period")
    },
    {
      key: "page_views",
      value: "547.9k",
      change: "-3.3%",
      trend: "down",
      compare: "566.8k",
      period: t("period")
    },
    {
      key: "engagement",
      value: "61.4%",
      change: "+4.2%",
      trend: "up",
      compare: "58.9%",
      period: t("period")
    },
    {
      key: "conversion",
      value: "8.4%",
      change: "-5.6%",
      trend: "down",
      compare: "8.9%",
      period: t("period")
    }
  ];

  return (
    <div className="overflow-hidden rounded-xl bg-card shadow-xs ring-1 ring-foreground/10" dir="rtl">
      <div className="grid divide-y *:data-[slot=card]:rounded-none *:data-[slot=card]:ring-0 md:grid-cols-2 md:divide-x md:divide-x-reverse md:divide-y-0 xl:grid-cols-5">
        {kpis.map((kpi) => (
          <Card key={kpi.key}>
            <CardHeader>
              <CardTitle className="font-normal text-sm text-right">{t(`${kpi.key}.title`)}</CardTitle>
              <CardAction>
                <Ellipsis className="size-4" />
              </CardAction>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 text-right">
              <div className="flex items-center justify-between gap-4">
                <div className="text-2xl leading-none tracking-tight" dir="ltr">{kpi.value}</div>
                <Badge 
                  className={kpi.trend === "up" 
                    ? "bg-green-500/10 text-green-700 dark:bg-green-500/15 dark:text-green-300 gap-0.5" 
                    : "bg-destructive/10 text-destructive gap-0.5"
                  } 
                  dir="ltr"
                >
                  {kpi.trend === "up" ? <ArrowUpRight className="size-3.5" /> : <ArrowDownRight className="size-3.5" />}
                  {kpi.change}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5 text-muted-foreground text-xs justify-start">
                <span>{t("compare")}</span>
                <span className="text-foreground" dir="ltr">{kpi.compare}</span>
                <span>•</span>
                <span>{kpi.period}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}