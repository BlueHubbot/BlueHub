"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export function WeeklySummaryCard() {
  const t = useTranslations("Productivity.weekly");

  return (
    <Card className="shadow-xs">
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardAction>
          <Button variant="ghost" size="sm" className="text-muted-foreground">
            {t("view_all")}
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-muted-foreground">{t("message")}</p>
        <div className="flex flex-col gap-2">
          <div className="font-medium">{t("progress_label")}</div>
          <Progress value={66} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
}