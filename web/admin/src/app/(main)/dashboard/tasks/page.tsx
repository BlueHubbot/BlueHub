"use client";

import { useTranslations } from "next-intl";
import { tasks } from "./_components/data";
import { Tasks } from "./_components/tasks";

export default function Page() {
  const t = useTranslations("Tasks");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-3xl tracking-tight">{t("welcome")}</h2>
        <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>
      <Tasks data={tasks} />
    </div>
  );
}