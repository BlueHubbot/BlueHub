"use client";

import { useTranslations } from "next-intl";
import { addDays, format } from "date-fns";
import { ClipboardCheck, Globe, Orbit, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const today = new Date();

export function ProjectsSection() {
  const t = useTranslations("Productivity.projects");

  const projects = [
    {
      key: "roadmap",
      title: t("items.roadmap.title"),
      status: t("status.in_progress"),
      description: t("items.roadmap.description"),
      progress: 68,
      due: `${t("due")} ${format(addDays(today, 9), "MMM d")}`,
      icon: Orbit,
    },
    {
      key: "redesign",
      title: t("items.redesign.title"),
      status: t("status.planning"),
      description: t("items.redesign.description"),
      progress: 42,
      due: `${t("due")} ${format(addDays(today, 21), "MMM d")}`,
      icon: Globe,
    },
    {
      key: "onboarding",
      title: t("items.onboarding.title"),
      status: t("status.planning"),
      description: t("items.onboarding.description"),
      progress: 31,
      due: `${t("due")} ${format(addDays(today, 18), "MMM d")}`,
      icon: ClipboardCheck,
    },
  ];

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xl tracking-tight">{t("title")}</h2>
        <div className="flex items-center gap-2">
          <Select defaultValue="active">
            <SelectTrigger className="w-28">
              <SelectValue placeholder={t("filter_placeholder")} />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="active">{t("filter.active")}</SelectItem>
                <SelectItem value="planning">{t("filter.planning")}</SelectItem>
                <SelectItem value="completed">{t("filter.completed")}</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
          <Button variant="outline">
            <Plus data-icon="inline-start" />
            {t("new")}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {projects.map((project) => (
          <Card key={project.key} className="shadow-xs">
            <CardHeader>
              <CardTitle>
                <div className="flex items-center gap-2">
                  <project.icon className="size-4 text-muted-foreground" />
                  <span>{project.title}</span>
                </div>
              </CardTitle>
              <CardAction>
                <Badge variant="outline">{project.status}</Badge>
              </CardAction>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-1">
                <div className="text-sm leading-none">{project.description}</div>
                <div className="flex items-center gap-3">
                  <Progress value={project.progress} className="h-2" />
                  <span className="shrink-0 text-sm">{project.progress}%</span>
                </div>
              </div>
            </CardContent>
            <CardFooter className="py-2.5">
              <span className="text-muted-foreground">{project.due}</span>
            </CardFooter>
          </Card>
        ))}
      </div>
    </section>
  );
}