"use client";

import { useTranslations } from "next-intl";
import { TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Item, ItemActions, ItemContent, ItemDescription, ItemMedia, ItemTitle } from "@/components/ui/item";

export function FinanceNotification() {
  const t = useTranslations("Finance.notification");

  return (
    <Item className="rounded-xl text-right" variant="outline">
      <ItemMedia variant="icon">
        <TrendingUp />
      </ItemMedia>
      <ItemContent>
        <ItemTitle>{t("title")}</ItemTitle>
        <ItemDescription>{t("description")}</ItemDescription>
      </ItemContent>
      <ItemActions>
        <Button size="sm" variant="outline">
          {t("button")}
        </Button>
      </ItemActions>
    </Item>
  );
}