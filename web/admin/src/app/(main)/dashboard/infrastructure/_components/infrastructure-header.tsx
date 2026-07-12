"use client";

import { useTranslations } from "next-intl";
import { Box, Container, Filter, PlusCircle, RefreshCw, Search, Server, Settings } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";
import { Kbd } from "@/components/ui/kbd";

export function InfrastructureHeader() {
  const t = useTranslations("Infrastructure");

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 flex-col gap-1">
            <h1 className="font-medium text-2xl leading-tight tracking-tight sm:text-3xl sm:leading-none">
              {t("title")}
            </h1>
            <p className="text-muted-foreground text-sm">
              {t("subtitle")}
            </p>
          </div>

          <div className="flex w-full items-center justify-between gap-2 sm:w-auto sm:justify-end">
            <span className="whitespace-nowrap text-muted-foreground text-sm">{t("last_updated")}</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon-sm">
                <RefreshCw />
              </Button>
              <Button variant="outline" size="icon-sm">
                <Settings data-icon="inline-start" />
              </Button>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="h-auto gap-1 rounded-sm px-1.5 py-0.5">
            <Container />
            {t("stats.projects", { count: 6 })}
          </Badge>
          <Badge variant="outline" className="h-auto gap-1 rounded-sm px-1.5 py-0.5">
            <Box />
            {t("stats.environments", { count: 16 })}
          </Badge>
          <Badge variant="outline" className="h-auto gap-1 rounded-sm px-1.5 py-0.5">
            <Server />
            {t("stats.servers", { count: 36 })}
          </Badge>
          <Badge variant="outline" className="h-auto gap-1 rounded-sm px-1.5 py-0.5">
            <span className="size-2 rounded-full bg-green-600 dark:bg-green-500" />
            {t("stats.uptime", { uptime: "99.93%" })}
          </Badge>
        </div>
      </div>

      <div className="flex flex-col gap-3 xl:flex-row">
        <InputGroup className="flex-1">
          <InputGroupAddon>
            <Search />
          </InputGroupAddon>
          <InputGroupInput placeholder={t("search_placeholder")} />
          <InputGroupAddon align="inline-end">
            <Kbd>⌘ K</Kbd>
          </InputGroupAddon>
        </InputGroup>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline">
            <PlusCircle data-icon="inline-start" />
            {t("filters.organization")}
          </Button>
          <Button variant="outline">
            <PlusCircle data-icon="inline-start" />
            {t("filters.stack")}
          </Button>
          <Button variant="outline">
            <PlusCircle data-icon="inline-start" />
            {t("filters.cloud_provider")}
          </Button>
          <Button variant="outline">
            <PlusCircle data-icon="inline-start" />
            {t("filters.project_type")}
          </Button>
          <Button variant="outline">
            <PlusCircle data-icon="inline-start" />
            {t("filters.environment")}
          </Button>
          <Button variant="outline">
            <Filter data-icon="inline-start" />
            {t("filters.filters")}
          </Button>
        </div>
      </div>
    </div>
  );
}