"use client";

import { useTranslations } from "next-intl";
import { SectionCards } from "./_components/section-cards";
import { ChartAreaInteractive } from "./_components/chart-area-interactive";
import { ProposalSectionsTable } from "./_components/proposal-sections-table/table";
import data from "./_components/data.json";

export default function Page() {
  const t = useTranslations("Legacy.Default");

  return (
    <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
      <div className="px-4 lg:px-6">
        <h1 className="text-3xl tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground text-sm">{t("subtitle")}</p>
      </div>
      <div className="px-4 lg:px-6">
        <SectionCards />
      </div>
      <div className="px-4 lg:px-6">
        <ChartAreaInteractive />
      </div>
      <div className="px-4 lg:px-6">
        <ProposalSectionsTable data={data} />
      </div>
    </div>
  );
}