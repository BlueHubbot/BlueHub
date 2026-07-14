"use client";

import { useTranslations } from "next-intl";
import { ArrowUpLeft, TrendingDown, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardDescription, CardHeader } from "@/components/ui/card";

export function KpiCards() {
  const t = useTranslations();

  return (
    <section className="space-y-5" dir="rtl">
      <div className="space-y-1 text-right">
        <h2 className="text-3xl tracking-tight font-bold">{t('pipeline_overview')}</h2>
        <p className="text-muted-foreground text-sm">
          {t('pipeline_description')}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {/* Lead Pipeline Value */}
        <Card>
          <CardHeader className="text-right">
            <CardDescription>{t('lead_pipeline_value')}</CardDescription>
            <CardAction className="left-6 right-auto">
              <ArrowUpLeft className="size-4" />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-2 text-right">
            <div className="flex items-center justify-between gap-3 flex-row-reverse">
              <span className="text-3xl leading-none tracking-tight ">$284,500</span>

              <Badge
                variant="outline"
                className="border-green-200 bg-green-500/10 text-green-700 dark:border-green-900/40 dark:bg-green-500/15 dark:text-green-300 "
              >
                <TrendingUp className="ml-1 size-3" />
                +12%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground ">$254,200</span>{" "}
              {t('last_month')}
            </p>
          </CardContent>
        </Card>

        {/* Qualified Lead Rate */}
        <Card>
          <CardHeader className="text-right">
            <CardDescription>{t('qualified_lead_rate')}</CardDescription>
            <CardAction className="left-6 right-auto">
              <ArrowUpLeft className="size-4" />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-2 text-right">
            <div className="flex items-center justify-between gap-3 flex-row-reverse">
              <span className="text-3xl leading-none tracking-tight ">28.4%</span>

              <Badge variant="outline" className="border-destructive/20 bg-destructive/10 text-destructive ">
                <TrendingDown className="ml-1 size-3" />
                -2.5%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground ">30.9%</span>{" "}
              {t('last_month')}
            </p>
          </CardContent>
        </Card>

        {/* Open Opportunities */}
        <Card>
          <CardHeader className="text-right">
            <CardDescription>{t('open_opportunities')}</CardDescription>
            <CardAction className="left-6 right-auto">
              <ArrowUpLeft className="size-4" />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-2 text-right">
            <div className="flex items-center justify-between gap-3 flex-row-reverse">
              <span className="text-3xl leading-none tracking-tight ">42</span>

              <Badge
                variant="outline"
                className="border-green-200 bg-green-500/10 text-green-700 dark:border-green-900/40 dark:bg-green-500/15 dark:text-green-300 "
              >
                <TrendingUp className="ml-1 size-3" />
                +7
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground ">35</span>{" "}
              {t('last_month')}
            </p>
          </CardContent>
        </Card>

        {/* Lead-to-Deal Rate */}
        <Card>
          <CardHeader className="text-right">
            <CardDescription>{t('lead_to_deal_rate')}</CardDescription>
            <CardAction className="left-6 right-auto">
              <ArrowUpLeft className="size-4" />
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-2 text-right">
            <div className="flex items-center justify-between gap-3 flex-row-reverse">
              <span className="text-3xl leading-none tracking-tight ">18.1%</span>

              <Badge
                variant="outline"
                className="border-green-200 bg-green-500/10 text-green-700 dark:border-green-900/40 dark:bg-green-500/15 dark:text-green-300 "
              >
                <TrendingUp className="ml-1 size-3" />
                +1.6%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground ">16.5%</span>{" "}
              {t('last_month')}
            </p>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}