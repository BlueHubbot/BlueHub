"use client";

import { useTranslations } from "next-intl";
import { TrendingDown, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export function SectionCards() {
  const t = useTranslations("Legacy.Default.cards");

  const cards = [
    {
      key: "revenue",
      value: "$1,250.00",
      change: "+12.5%",
      trend: "up",
      title: t("revenue.title"),
      footer: t("revenue.footer"),
      footer_sub: t("revenue.footer_sub"),
    },
    {
      key: "customers",
      value: "1,234",
      change: "-20%",
      trend: "down",
      title: t("customers.title"),
      footer: t("customers.footer"),
      footer_sub: t("customers.footer_sub"),
    },
    {
      key: "accounts",
      value: "45,678",
      change: "+12.5%",
      trend: "up",
      title: t("accounts.title"),
      footer: t("accounts.footer"),
      footer_sub: t("accounts.footer_sub"),
    },
    {
      key: "growth",
      value: "4.5%",
      change: "+4.5%",
      trend: "up",
      title: t("growth.title"),
      footer: t("growth.footer"),
      footer_sub: t("growth.footer_sub"),
    },
  ];

  return (
    <div className="grid @5xl/main:grid-cols-4 @xl/main:grid-cols-2 grid-cols-1 gap-4 *:data-[slot=card]:bg-linear-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs dark:*:data-[slot=card]:bg-card">
      {cards.map((card) => (
        <Card key={card.key} className="@container/card">
          <CardHeader>
            <CardDescription>{card.title}</CardDescription>
            <CardTitle className="font-semibold @[250px]/card:text-3xl text-2xl">{card.value}</CardTitle>
            <CardAction>
              <Badge variant="outline">
                {card.trend === "up" ? <TrendingUp /> : <TrendingDown />}
                {card.change}
              </Badge>
            </CardAction>
          </CardHeader>
          <CardFooter className="flex-col items-start gap-1.5 text-sm">
            <div className="line-clamp-1 flex gap-2 font-medium">
              {card.footer} {card.trend === "up" ? <TrendingUp className="size-4" /> : <TrendingDown className="size-4" />}
            </div>
            <div className="text-muted-foreground">{card.footer_sub}</div>
          </CardFooter>
        </Card>
      ))}
    </div>
  );
}