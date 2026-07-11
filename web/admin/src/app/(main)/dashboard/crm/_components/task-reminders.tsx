"use client";

import { useTranslations, useLocale } from "next-intl";
import { CalendarDays, CalendarRange } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const proposalSent = 12;
const proposalGoal = 18;
const proposalProgressPercentage = Math.round((proposalSent / proposalGoal) * 100);
const proposalGoalBarCount = 42;
const activeProposalBars = Math.round((proposalSent / proposalGoal) * proposalGoalBarCount);

const proposalGoalBars = Array.from({ length: proposalGoalBarCount }, (_, index) => ({
  id: `proposal-goal-${index + 1}`,
  active: index < activeProposalBars,
}));

export function TaskReminders() {
  const t = useTranslations();
  const locale = useLocale();

  return (
    <section className="grid grid-cols-1 gap-4 xl:grid-cols-12" dir="rtl">
      {/* Upcoming Meetings */}
      <Card className="xl:col-span-8">
        <CardHeader className="text-right">
          <CardTitle className="font-bold">{t('upcoming_meetings')}</CardTitle>
          <CardAction className="left-6 right-auto">
            <Button variant="outline" size="sm" className="">
              <CalendarDays className="ml-2 size-4" />
              {t('view_calendar')}
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            <div className="flex items-center justify-between text-muted-foreground text-xs  flex-row-reverse">
              <div className="flex flex-col items-center gap-1">
                <span>08:45</span>
                <span className="h-2 w-px bg-border" />
              </div>
              <div className="flex flex-col items-center gap-1">
                <span>09:00</span>
                <span className="h-2 w-px bg-border" />
              </div>
              <div className="flex flex-col items-center gap-1">
                <span>10:00</span>
                <span className="h-2 w-px bg-border" />
              </div>
              <div className="flex flex-col items-center gap-1">
                <span>10:20</span>
                <span className="h-2 w-px bg-border" />
              </div>
            </div>

            <div className="relative h-14">
              <div className="absolute inset-x-3 top-1/2 h-px -translate-y-1/2 bg-border/80" />
              {/* تراز بندی جلسه از سمت راست به جای چپ برای ساختار RTL */}
              <div className="absolute top-2 bottom-2 right-[22%] flex w-[44%] items-center rounded-lg bg-primary px-3 text-primary-foreground shadow-sm text-right">
                <div className="flex items-center gap-2 flex-row-reverse w-full justify-end">
                  <div className="min-w-0 text-right">
                    <div className="truncate font-medium text-primary-foreground text-xs leading-none">
                      دموی محصول با تیم
                    </div>
                    <div className="truncate text-[10px] text-primary-foreground/75 mt-1">استودیو وب‌لابز</div>
                  </div>
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-background text-primary">
                    <CalendarRange className="size-3.5" />
                  </div>
                </div>
              </div>
              <div className="absolute top-4 bottom-4 right-[64%] w-1 rounded-full bg-background/90" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Monthly Proposal Goal */}
      <Card className="xl:col-span-4">
        <CardHeader className="text-right">
          <CardTitle className="font-bold">{t('monthly_proposal_goal')}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1 text-right">
          <div className="flex items-end justify-between gap-3 flex-row-reverse">
            <div className="font-medium text-2xl  leading-none">
              {proposalSent.toLocaleString(locale)} <span className="font-normal text-base text-muted-foreground">{t('sent')}</span>
            </div>
            <div className="text-muted-foreground text-sm ">
              {t('target')} {proposalGoal.toLocaleString(locale)}
            </div>
          </div>
          <div className="flex h-10 w-full items-end gap-0.5 flex-row-reverse">
            {proposalGoalBars.map((bar) => (
              <div key={bar.id} className="flex flex-1 justify-center">
                <div
                  className={cn(
                    "h-10 w-1.5 rounded-full",
                    bar.active ? "bg-muted-foreground/75" : "bg-muted-foreground/25",
                  )}
                />
              </div>
            ))}
          </div>
          <p className="text-muted-foreground text-sm mt-1">
            {t('proposal_target_reached', { percent: proposalProgressPercentage.toLocaleString(locale) })}
          </p>
        </CardContent>
      </Card>
    </section>
  );
}