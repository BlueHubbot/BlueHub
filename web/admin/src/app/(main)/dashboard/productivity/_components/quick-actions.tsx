"use client";

import { useTranslations } from "next-intl";
import { CheckSquare, FileText, Focus, Orbit, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";

export function QuickActions() {
  const t = useTranslations("Productivity.quick_actions");

  const quickActions = [
    { key: "new_note", icon: FileText },
    { key: "new_task", icon: CheckSquare },
    { key: "new_project", icon: Orbit },
    { key: "new_goal", icon: Focus },
    { key: "upload", icon: Upload },
  ] as const;

  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-xl tracking-tight">{t("title")}</h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {quickActions.map((action) => (
          <Button key={action.key} variant="outline" className="justify-start">
            <action.icon data-icon="inline-start" />
            {t(action.key)}
          </Button>
        ))}
      </div>
    </section>
  );
}