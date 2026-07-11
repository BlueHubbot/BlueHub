"use client";

import { useTranslations } from "next-intl";
import { format } from "date-fns";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ClassSchedule() {
  const t = useTranslations("Academy.schedule");
  const today = format(new Date(), "EEEE, d MMMM");

  const classes = [
    {
      time: "08:00 - 08:45",
      title: t("classes.mathematics"),
      details: "Grade 11A • Room 2.14",
      status: "in_progress",
      color: "green"
    },
    {
      time: "09:00 - 09:45",
      title: t("classes.literature"),
      details: "Grade 11B • Seminar Room 3",
      status: "upcoming",
      color: "yellow"
    },
    {
      time: "10:00 - 10:45",
      title: t("classes.physics"),
      details: "Grade 11C • Physics Lab",
      status: "upcoming",
      color: "yellow"
    },
    {
      time: "11:00 - 11:45",
      title: t("classes.history"),
      details: "Grade 11A • Room 1.08",
      status: "cancelled",
      color: "destructive"
    },
    {
      time: "12:00 - 12:45",
      title: t("classes.computer_science"),
      details: "Grade 11B • Computing Lab",
      status: "upcoming",
      color: "yellow"
    }
  ];

  const statusColors = {
    in_progress: {
      badge: "border-green-600/50 bg-green-50 text-green-600 dark:border-green-800/50 dark:bg-green-500/10 dark:text-green-400",
      dot: "bg-green-600 dark:bg-green-400"
    },
    upcoming: {
      badge: "border-yellow-600/50 bg-yellow-50 text-yellow-700 dark:border-yellow-800/50 dark:bg-yellow-500/10 dark:text-yellow-300",
      dot: "bg-yellow-500 dark:bg-yellow-400"
    },
    cancelled: {
      badge: "border-destructive/50 bg-destructive/10 text-destructive dark:border-destructive/50 dark:bg-destructive/20",
      dot: "bg-destructive"
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{t("title")}</CardTitle>
        <CardAction className="flex items-center gap-1 text-muted-foreground text-xs">
          {t("view_full")} <ArrowRight className="size-4" />
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-0">
        <div className="flex flex-col divide-y divide-border">
          {classes.map((cls, index) => (
            <div 
              key={index} 
              className="grid grid-cols-1 gap-3 bg-card py-3 transition-colors hover:bg-muted/30 sm:grid-cols-[10rem_1fr_auto] sm:items-center"
            >
              <div className="flex gap-2">
                <div className={`w-1 shrink-0 rounded-md ${statusColors[cls.status as keyof typeof statusColors].dot}`} />
                <div className="text-nowrap text-xs">
                  <div className="font-medium text-foreground">{cls.time}</div>
                  <div className="text-muted-foreground">{today}</div>
                </div>
              </div>

              <div className="flex min-w-0 flex-col gap-1">
                <div className="truncate font-medium text-foreground text-sm leading-none">{cls.title}</div>
                <div className="truncate text-muted-foreground text-xs leading-none">{cls.details}</div>
              </div>

              <Badge
                variant="secondary"
                className={`shrink-0 rounded-md px-2.5 py-1 font-medium text-[10px] ${statusColors[cls.status as keyof typeof statusColors].badge}`}
              >
                {t(`status.${cls.status}`)}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}