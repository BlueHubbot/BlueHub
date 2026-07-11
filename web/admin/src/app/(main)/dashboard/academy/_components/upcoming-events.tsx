"use client";

import { useTranslations } from "next-intl";
import { addDays, format } from "date-fns";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function UpcomingEvents() {
  const t = useTranslations("Academy.events");
  const today = new Date();

  const upcomingEvents = [
    { dayOffset: 6, key: "exhibition" },
    { dayOffset: 9, key: "parents_evening" },
    { dayOffset: 12, key: "sports_day" },
    { dayOffset: 15, key: "mock_exam" },
    { dayOffset: 18, key: "department_planning" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{t("title")}</CardTitle>
        <CardAction className="flex items-center gap-1 text-muted-foreground text-xs">
          {t("view_calendar")} <ArrowRight className="size-4" />
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {upcomingEvents.map((event) => {
          const eventDate = addDays(today, event.dayOffset);
          const eventData = t.raw(`items.${event.key}`);

          return (
            <div key={event.key} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="size-11 shrink-0 overflow-hidden rounded-sm border">
                  <div className="grid h-1/3 place-items-center border-b bg-muted font-medium text-[10px] uppercase leading-none">
                    {format(eventDate, "MMM")}
                  </div>
                  <div className="grid h-2/3 place-items-center text-lg leading-none">{format(eventDate, "d")}</div>
                </div>

                <div className="flex min-w-0 flex-col gap-1">
                  <div className="truncate font-medium text-sm leading-none">{eventData.title}</div>
                  <div className="text-muted-foreground text-xs leading-none">{eventData.time}</div>
                </div>
              </div>
              <Badge variant="outline" className="shrink-0 rounded-md px-2.5 py-1 font-medium text-[10px]">
                {eventData.type}
              </Badge>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}