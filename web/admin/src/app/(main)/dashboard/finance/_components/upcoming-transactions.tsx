"use client";

import { useTranslations } from "next-intl";
import { addDays, format, set } from "date-fns";
import { ChevronLeft, Zap } from "lucide-react";
import { siClaude, siLinear, siResend } from "simple-icons";

import { SimpleIcon } from "@/components/simple-icon";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle } from "@/components/ui/item";

export function UpcomingTransactions() {
  const t = useTranslations("Finance.upcoming");

  const transactions = [
    {
      id: 1,
      title: t("items.claude"),
      date: format(set(addDays(new Date(), 2), { hours: 14, minutes: 45 }), "HH:mm '•' yyyy/MM/dd"),
      icon: siClaude,
    },
    {
      id: 2,
      title: t("items.resend"),
      date: format(set(addDays(new Date(), 4), { hours: 7, minutes: 0 }), "HH:mm '•' yyyy/MM/dd"),
      icon: siResend,
    },
    {
      id: 3,
      title: t("items.linear"),
      date: format(set(addDays(new Date(), 10), { hours: 7, minutes: 0 }), "HH:mm '•' yyyy/MM/dd"),
      icon: siLinear,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-normal">{t("title")}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <h2 className="flex items-baseline text-3xl leading-none tracking-tight">
              <span className="font-normal">$1,245</span>
              <span className="text-muted-foreground text-xl">.00</span>
            </h2>
            <p className="text-muted-foreground text-sm leading-none">
              {t("subtitle_start")} <span className="font-medium text-foreground">۳</span> {t("subtitle_end")}
            </p>
          </div>
          <div className="flex w-max items-center gap-2 rounded-md border border-border bg-muted/70 px-2 py-1.5 text-sm">
            <Zap className="size-4 fill-primary text-primary" />
            <span className="text-muted-foreground">
              {t("auto_pay_start")} <span className="font-medium text-foreground">$145.00</span> {t("auto_pay_end")}
            </span>
          </div>
        </div>

        <ItemGroup>
          {transactions.map((transaction) => (
            <Item key={transaction.id} variant="outline" size="xs">
              <ItemMedia>
                <div className="grid size-9 place-items-center rounded-md border bg-background">
                  <SimpleIcon icon={transaction.icon} />
                </div>
              </ItemMedia>
              <ItemContent>
                <ItemTitle>{transaction.title}</ItemTitle>
                <ItemDescription>{transaction.date}</ItemDescription>
              </ItemContent>
              <ItemActions>
                <ChevronLeft className="size-5 text-muted-foreground" />
              </ItemActions>
            </Item>
          ))}
        </ItemGroup>
      </CardContent>
    </Card>
  );
}