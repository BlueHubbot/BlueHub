"use client";

import { useTranslations } from "next-intl";
import { ActionsManagerQueue } from "./_components/analytics-actions-manager-queue";
import { ActionsRiskLedger } from "./_components/analytics-actions-risk-ledger";
import { DriversCoverageTriage } from "./_components/analytics-drivers-coverage-triage";
import { DriversForecastTarget } from "./_components/analytics-drivers-forecast-target";
import { AnalyticsOverview } from "./_components/analytics-overview";

export default function Page() {
  const t = useTranslations("Legacy.Analytics");

  return (
    <div className="flex flex-col gap-4 md:gap-6">
      <div className="px-4 lg:px-6">
        <h1 className="text-3xl tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground text-sm">{t("subtitle")}</p>
      </div>
      <AnalyticsOverview />

      <div className="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <DriversForecastTarget />
          <DriversCoverageTriage />
        </div>
        <ActionsManagerQueue />
      </div>

      <ActionsRiskLedger />
    </div>
  );
}