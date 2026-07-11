"use client";

import { useTranslations } from "next-intl";
import { recentLeadsData } from "./_components/crm.config";
import { InsightCards } from "./_components/insight-cards";
import { OperationalCards } from "./_components/operational-cards";
import { OverviewCards } from "./_components/overview-cards";
import { RecentLeadsTable } from "./_components/recent-leads-table/table";

export default function Page() {
  const t = useTranslations("Legacy.CRM");

  return (
    <div className="flex flex-col gap-4 md:gap-6">
      <div className="px-4 lg:px-6">
        <h1 className="text-3xl tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground text-sm">{t("subtitle")}</p>
      </div>
      <OverviewCards />
      <InsightCards />
      <OperationalCards />
      <RecentLeadsTable data={recentLeadsData} />
    </div>
  );
}