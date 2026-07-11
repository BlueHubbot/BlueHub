"use client";

import { useTranslations } from "next-intl";
import { Save, Send } from "lucide-react";

import { Button } from "@/components/ui/button";

import { Invoice } from "./_components/invoice";

export default function Page() {
  const t = useTranslations("Invoice");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="font-medium text-3xl leading-none tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground text-sm">
            {t("subtitle")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline">
            <Save data-icon="inline-start" />
            {t("save_draft")}
          </Button>
          <Button type="button">
            <Send data-icon="inline-start" />
            {t("send_invoice")}
          </Button>
        </div>
      </div>

      <Invoice />
    </div>
  );
}