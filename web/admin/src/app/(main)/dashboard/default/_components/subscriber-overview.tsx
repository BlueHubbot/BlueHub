"use client";

import { useTranslations } from 'next-intl';
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { RecentCustomersTable } from "./recent-customers-table/table";
import customersData from "./data.json";

export function SubscriberOverview() {
  const t = useTranslations();

  return (
    <Card className="flex flex-col gap-4">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <CardTitle>{t('recent_customers')}</CardTitle>
          <CardDescription>{t('recent_customers_description')}</CardDescription>
        </div>
        <CardAction>
          <Button variant="outline" size="sm">
            <Download /> {t('export')}
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        <RecentCustomersTable data={customersData} />
      </CardContent>
    </Card>
  );
}