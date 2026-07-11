"use client";

import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function DriversCoverageTriage() {
  const t = useTranslations("Legacy.Analytics.coverage");

  const leverOptions = [
    {
      key: "deal",
      label: t("levers.deal.label"),
      value: t("levers.deal.value"),
      context: t("levers.deal.context"),
    },
    {
      key: "conversion",
      label: t("levers.conversion.label"),
      value: t("levers.conversion.value"),
      context: t("levers.conversion.context"),
    },
    {
      key: "cycle",
      label: t("levers.cycle.label"),
      value: t("levers.cycle.value"),
      context: t("levers.cycle.context"),
    },
  ] as const;

  return (
    <Card className="shadow-xs">
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="destructive" className="rounded-md font-medium">
            {t("at_risk")}
          </Badge>
          <Badge variant="outline" className="font-medium">
            1.9x / 3.0x
          </Badge>
          <Badge variant="outline" className="font-medium">
            {t("gap")} $222,930
          </Badge>
          <Badge variant="outline" className="font-medium">
            4 {t("deals")} • ETA 10d
          </Badge>
        </div>

        <p className="text-muted-foreground text-xs">{t("coverage_note")}</p>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {leverOptions.map((lever) => (
            <div key={lever.key} className="space-y-1 rounded-md border bg-muted/20 px-2.5 py-2">
              <p className="text-muted-foreground text-xs">{lever.label}</p>
              <p className="font-semibold text-sm">{lever.value}</p>
              <p className="text-muted-foreground text-xs">{lever.context}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-muted/20 px-3 py-2">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="text-muted-foreground">
              {t("owner")}: <span className="font-medium text-foreground">Leila Zhang</span>
            </span>
            <span className="text-muted-foreground">
              {t("focus")}: <span className="text-foreground">{t("focus_value")}</span>
            </span>
            <span className="text-muted-foreground">
              {t("due")}: <span className="text-foreground">{t("due_value")}</span>
            </span>
          </div>
          <Button variant="secondary" size="sm" className="h-7 px-3 text-xs">
            {t("open_deals")}
          </Button>
        </div>

        <div className="space-y-1 rounded-md border border-dashed bg-muted/10 px-3 py-2.5">
          <p className="text-muted-foreground text-xs">
            {t("fastest_path")}: <span className="font-medium text-foreground">{t("fastest_path_value")}</span>
          </p>
          <p className="text-muted-foreground text-xs">
            {t("priority_sequence")}: <span className="text-foreground">{t("priority_sequence_value")}</span>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}