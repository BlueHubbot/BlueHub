"use client";

import { useTranslations } from "next-intl";
import { Ellipsis } from "lucide-react";

import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function TopPages() {
  const t = useTranslations("Analytics.pages");

  const pages = [
    { path: "/dashboard", views: "۶۴.۲k", time: "۳ دقیقه ۱۲ ثانیه", bounce: "۲۴٪" },
    { path: "/pricing", views: "۴۱.۸k", time: "۲ دقیقه ۰۸ ثانیه", bounce: "۳۱٪" },
    { path: "/docs/getting-started", views: "۲۸.۶k", time: "۴ دقیقه ۴۴ ثانیه", bounce: "۱۸٪" },
    { path: "/blog/analytics-guide", views: "۱۹.۳k", time: "۵ دقیقه ۰۶ ثانیه", bounce: "۲۲٪" },
    { path: "/contact", views: "۸.۹k", time: "۱ دقیقه ۱۸ ثانیه", bounce: "۴۲٪" },
  ];

  return (
    <Card className="h-full gap-2" dir="rtl">
      <CardHeader>
        <CardTitle className="font-normal text-right">{t("title")}</CardTitle>
        <CardAction>
          <Ellipsis className="size-4" />
        </CardAction>
      </CardHeader>

      <CardContent className="px-0">
        <Table className="[&_td:first-child]:pr-4 [&_td:last-child]:pl-4 [&_th:first-child]:pr-4 [&_th:last-child]:pl-4">
          <TableHeader className="[&_tr]:border-border/50">
            <TableRow className="hover:bg-transparent">
              <TableHead className="h-8 text-right font-normal">{t("path")}</TableHead>
              <TableHead className="h-8 w-24 text-left font-normal">{t("views")}</TableHead>
              <TableHead className="h-8 w-28 text-left font-normal">{t("avg_time")}</TableHead>
              <TableHead className="h-8 w-20 text-left font-normal">{t("bounce_rate")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="[&_tr]:border-border/50">
            {pages.map((page) => (
              <TableRow className="hover:bg-transparent" key={page.path}>
                <TableCell className="max-w-0 truncate py-4 font-medium text-right" dir="ltr">
                  {page.path}
                </TableCell>
                <TableCell className="text-left" dir="ltr">{page.views}</TableCell>
                <TableCell className="text-left text-muted-foreground">{page.time}</TableCell>
                <TableCell className="text-left text-muted-foreground">{page.bounce}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}