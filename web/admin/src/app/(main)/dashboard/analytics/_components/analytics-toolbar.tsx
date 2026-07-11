"use client";

import { useTranslations } from "next-intl";
import { Ellipsis, FileDown, FileUp, RefreshCw, Share2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function AnalyticsToolbar() {
  const t = useTranslations("Analytics.toolbar");

  return (
    <div className="flex items-center gap-2">
      <Select defaultValue="last-4-weeks">
        <SelectTrigger className="w-38">
          <SelectValue placeholder={t("select_placeholder")} />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectItem value="last-7-days">{t("periods.last_7_days")}</SelectItem>
            <SelectItem value="last-4-weeks">{t("periods.last_4_weeks")}</SelectItem>
            <SelectItem value="last-3-months">{t("periods.last_3_months")}</SelectItem>
            <SelectItem value="year-to-date">{t("periods.year_to_date")}</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button size="icon" variant="outline" aria-label={t("more_actions")}>
            <Ellipsis />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48 text-right">
          <DropdownMenuGroup>
            <DropdownMenuLabel className="text-right">{t("report_actions")}</DropdownMenuLabel>
            <DropdownMenuItem className="flex items-center justify-between gap-2">
              <span className="flex-1 text-right">{t("export_report")}</span>
              <FileDown className="size-4 shrink-0" />
            </DropdownMenuItem>
            <DropdownMenuItem className="flex items-center justify-between gap-2">
              <span className="flex-1 text-right">{t("import_data")}</span>
              <FileUp className="size-4 shrink-0" />
            </DropdownMenuItem>
            <DropdownMenuItem className="flex items-center justify-between gap-2">
              <span className="flex-1 text-right">{t("share_dashboard")}</span>
              <Share2 className="size-4 shrink-0" />
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem className="flex items-center justify-between gap-2">
              <span className="flex-1 text-right">{t("refresh_metrics")}</span>
              <RefreshCw className="size-4 shrink-0" />
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}