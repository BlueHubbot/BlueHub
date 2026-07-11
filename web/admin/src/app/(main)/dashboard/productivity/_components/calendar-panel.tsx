"use client";

import * as React from "react";
import { useLocale } from "next-intl";
import { startOfMonth, startOfToday } from "date-fns";
import { enUS, faIR } from "date-fns/locale";

import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent } from "@/components/ui/card";

export function CalendarPanel() {
  const locale = useLocale();
  const today = startOfToday();
  const [date, setDate] = React.useState<Date | undefined>(today);
  const [currentMonth, setCurrentMonth] = React.useState<Date>(() => startOfMonth(today));

  const dateFnsLocale = locale === "fa" ? faIR : enUS;

  return (
    <Card className="w-full" size="sm">
      <CardContent>
        <Calendar
          mode="single"
          selected={date}
          onSelect={setDate}
          month={currentMonth}
          onMonthChange={setCurrentMonth}
          fixedWeeks
          locale={dateFnsLocale}
          className="w-full p-0"
        />
      </CardContent>
    </Card>
  );
}