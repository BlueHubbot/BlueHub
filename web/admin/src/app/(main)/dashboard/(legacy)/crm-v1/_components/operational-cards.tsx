"use client";

import { useTranslations } from "next-intl";
import { Clock } from "lucide-react";
import { Funnel, FunnelChart, LabelList } from "recharts";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer } from "@/components/ui/chart";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { cn, formatCurrency } from "@/lib/utils";

import { actionItems, regionSalesData, salesPipelineChartConfig, salesPipelineChartData } from "./crm.config";

export function OperationalCards() {
  const t = useTranslations("Legacy.CRM.operational");
  const totalSales = regionSalesData.reduce((sum, region) => sum + region.sales, 0);

  return (
    <div className="grid grid-cols-1 gap-4 *:data-[slot=card]:shadow-xs sm:grid-cols-2 xl:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle>{t("sales_pipeline")}</CardTitle>
        </CardHeader>
        <CardContent className="size-full">
          <ChartContainer config={salesPipelineChartConfig} className="size-full">
            <FunnelChart margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
              <Funnel className="stroke-2 stroke-card" dataKey="value" data={salesPipelineChartData}>
                <LabelList className="fill-foreground stroke-0" dataKey="stage" position="right" offset={10} />
                <LabelList className="fill-foreground stroke-0" dataKey="value" position="left" offset={10} />
              </Funnel>
            </FunnelChart>
          </ChartContainer>
        </CardContent>
        <CardFooter>
          <p className="text-muted-foreground text-xs">{t("pipeline_footer")}</p>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("sales_by_region")}</CardTitle>
          <CardDescription className="font-medium">
            {formatCurrency(totalSales, { noDecimals: true })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2.5">
            {regionSalesData.map((region) => (
              <div key={region.region} className="space-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{region.region}</span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-semibold text-sm">
                      {formatCurrency(region.sales, { noDecimals: true })}
                    </span>
                    <span
                      className={cn(
                        "font-medium text-xs",
                        region.isPositive ? "text-green-500" : "text-destructive",
                      )}
                    >
                      {region.growth}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Progress value={region.percentage} />
                  <span className="font-medium text-muted-foreground text-xs">{region.percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
        <CardFooter>
          <div className="flex justify-between gap-1 text-muted-foreground text-xs">
            <span>{t("regions_tracked", { count: regionSalesData.length })}</span>
            <span>•</span>
            <span>{t("regions_growing", { count: regionSalesData.filter((r) => r.isPositive).length })}</span>
          </div>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("action_items")}</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2.5">
            {actionItems.map((item) => (
              <li key={item.id} className="space-y-2 rounded-md border px-3 py-2">
                <div className="flex items-center gap-2">
                  <Checkbox defaultChecked={item.checked} />
                  <span className="font-medium text-sm">{t(`actions.${item.id}.title`)}</span>
                  <span
                    className={cn(
                      "w-fit rounded-md px-2 py-1 font-medium text-xs",
                      item.priority === "High" && "bg-destructive/20 text-destructive",
                      item.priority === "Medium" && "bg-yellow-500/20 text-yellow-500",
                      item.priority === "Low" && "bg-green-500/20 text-green-500",
                    )}
                  >
                    {t(`priority.${item.priority.toLowerCase()}`)}
                  </span>
                </div>
                <div className="font-medium text-muted-foreground text-xs">{t(`actions.${item.id}.desc`)}</div>
                <div className="flex items-center gap-1">
                  <Clock className="size-3 text-muted-foreground" />
                  <span className="font-medium text-muted-foreground text-xs">{t(`actions.${item.id}.due`)}</span>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}