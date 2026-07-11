"use client";

import { useTranslations } from "next-intl";
import { ArrowUp, Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function KpiCards() {
  const t = useTranslations("Academy.kpis");

  const kpis = [
    {
      key: "students",
      value: "128",
      change: "+2.8%",
      trend: "up",
      description: t("students.description")
    },
    {
      key: "attendance",
      value: "94.2%",
      change: "+1.1%",
      trend: "up",
      description: t("attendance.description")
    },
    {
      key: "assignments",
      value: "81",
      change: null,
      trend: null,
      description: t("assignments.description")
    },
    {
      key: "classes",
      value: "5",
      change: null,
      trend: null,
      description: t("classes.description")
    }
  ];

  return (
    <section className="space-y-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <Card key={kpi.key}>
            <CardHeader>
              <CardTitle className="text-sm">{t(`${kpi.key}.title`)}</CardTitle>
              <CardAction>
                <Info className="size-3 text-muted-foreground" />
              </CardAction>
            </CardHeader>
            <CardContent className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-3xl text-foreground leading-none tracking-tight">{kpi.value}</span>
                {kpi.change && (
                  <Badge 
                    className={kpi.trend === "up" 
                      ? "rounded-sm border-green-600/50 bg-green-500/10 px-1 font-normal text-green-700 text-xs dark:border-green-800/50 dark:bg-green-500/15 dark:text-green-300"
                      : "rounded-sm border-destructive/50 bg-destructive/10 px-1 font-normal text-destructive text-xs"
                    }
                  >
                    <ArrowUp className={kpi.trend === "down" ? "rotate-180" : ""} />
                    {kpi.change}
                  </Badge>
                )}
              </div>
              <div className="text-right text-muted-foreground text-xs">{kpi.description}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}