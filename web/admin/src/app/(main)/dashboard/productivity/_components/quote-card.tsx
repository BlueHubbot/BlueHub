"use client";

import { useTranslations } from "next-intl";
import { Quote } from "lucide-react";

export function QuoteCard() {
  const t = useTranslations("Productivity.quote");

  return (
    <section className="rounded-2xl border bg-card p-6 shadow-xs">
      <div className="flex items-start gap-4">
        <div className="grid size-8 shrink-0 place-items-center text-muted-foreground">
          <Quote className="size-6" />
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-xl leading-none tracking-tight">{t("text")}</p>
          <p className="text-muted-foreground">{t("subtext")}</p>
        </div>
      </div>
    </section>
  );
}