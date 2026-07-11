"use client";

import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export function IncomeBreakdown() {
  const t = useTranslations("Finance.income");

  const incomeSources = [
    { key: "salary", percent: "68%", amount: "$4,560.00" },
    { key: "freelance", percent: "21%", amount: "$1,412.00" },
    { key: "dividends", percent: "11%", amount: "$765.00" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-normal">{t("title")}</CardTitle>
      </CardHeader>

      <CardContent className="grid grid-cols-1 gap-1 md:grid-cols-3">
        {incomeSources.map((source, index) => (
          <section key={source.key} className="isolate flex gap-[0.5px]">
            <Separator
              orientation="vertical"
              className="mb-1 h-auto self-auto border-muted-foreground/50 border-r border-dashed bg-transparent"
            />
            <div className="flex min-h-24 flex-1 flex-col justify-between text-right">
              <div className="flex min-w-0 flex-col gap-1 px-1">
                <p className="wrap-break-word text-muted-foreground text-xs leading-none">
                  {t(`${source.key}.label`)} · {source.percent}
                </p>
                <div className="text-lg leading-none tracking-tight" dir="ltr">{source.amount}</div>
              </div>
              <div 
                className="-mr-0.5 h-5 rounded-sm" 
                style={{ 
                  backgroundColor: `var(--chart-${index === 0 ? '3' : index === 1 ? '3/75' : '3/50'})` 
                }} 
              />
            </div>
          </section>
        ))}
      </CardContent>
    </Card>
  );
}