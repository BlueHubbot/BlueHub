"use client";

import { useTranslations } from "next-intl";
import { ArrowUpRight } from "lucide-react";

import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export function TopProducts() {
  const t = useTranslations("Ecommerce.products");

  const categories = [
    { name: t("categories.apparel"), share: 44, color: "var(--chart-3)" },
    { name: t("categories.accessories"), share: 32, color: "var(--chart-2)" },
    { name: t("categories.home"), share: 24, color: "var(--chart-1)" },
  ];

  const products = [
    { name: t("items.overshirt"), category: t("categories.apparel"), share: "31%", sales: "$14,820" },
    { name: t("items.tote"), category: t("categories.accessories"), share: "24%", sales: "$11,460" },
    { name: t("items.planter"), category: t("categories.home"), share: "18%", sales: "$8,930" },
  ];

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="font-normal text-muted-foreground text-sm">{t("title")}</CardTitle>
        <CardDescription className="text-foreground text-xl leading-none tracking-tight">
          {t("sales_share")}
        </CardDescription>
        <CardAction>
          <ArrowUpRight className="size-4" />
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <div aria-label={t("category_label")} className="flex h-2 gap-1 overflow-hidden bg-muted" role="img">
            {categories.map((category) => (
              <div
                aria-hidden="true"
                key={category.name}
                className="rounded-md"
                style={{
                  backgroundColor: category.color,
                  width: `${category.share}%`,
                }}
              />
            ))}
          </div>

          <div className="flex flex-wrap gap-4">
            {categories.map((category) => (
              <div className="flex items-center gap-1" key={category.name}>
                <span aria-hidden="true" className="size-2 rounded-full" style={{ backgroundColor: category.color }} />
                <span className="text-muted-foreground text-xs">{category.name}</span>
              </div>
            ))}
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 gap-y-3">
          <div className="text-muted-foreground text-xs">{t("products_label")}</div>
          <div className="text-muted-foreground text-xs">{t("share_label")}</div>
          <div className="text-muted-foreground text-xs">{t("sales_label")}</div>

          {products.map((product) => (
            <div className="contents text-sm" key={product.name}>
              <div className="min-w-0">
                <div className="truncate font-medium">{product.name}</div>
                <div className="text-muted-foreground text-xs">{product.category}</div>
              </div>
              <div className="self-center text-muted-foreground">{product.share}</div>
              <div className="self-center font-medium">{product.sales}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}