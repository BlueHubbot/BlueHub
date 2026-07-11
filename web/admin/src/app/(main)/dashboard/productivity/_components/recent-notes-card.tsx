"use client";

import { useTranslations } from "next-intl";
import { format, isToday, isYesterday, subDays } from "date-fns";
import { BookOpen, FileText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const today = new Date();

function formatNoteDate(date: Date) {
  if (isToday(date)) return "Today";
  if (isYesterday(date)) return "Yesterday";
  return format(date, "MMM d");
}

export function RecentNotesCard() {
  const t = useTranslations("Productivity.notes");

  const recentNotes = [
    { title: t("items.design_principles"), date: formatNoteDate(today), icon: FileText },
    { title: t("items.content_ideas"), date: formatNoteDate(subDays(today, 1)), icon: FileText },
    { title: t("items.lessons"), date: formatNoteDate(subDays(today, 4)), icon: FileText },
    { title: t("items.books"), date: formatNoteDate(subDays(today, 5)), icon: BookOpen },
  ];

  return (
    <Card className="shadow-xs">
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardAction>
          <Button variant="ghost" size="sm" className="text-muted-foreground">
            {t("view_all")}
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {recentNotes.map((note) => (
          <div key={note.title} className="flex items-start gap-4">
            <note.icon className="size-5 text-muted-foreground" />
            <div className="min-w-0">
              <div className="truncate font-medium text-sm leading-none">{note.title}</div>
              <div className="text-muted-foreground text-xs">{note.date}</div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}