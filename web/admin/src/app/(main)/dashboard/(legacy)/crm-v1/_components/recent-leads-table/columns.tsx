"use client";
"use no memo";

import { useTranslations } from "next-intl";
import type { ColumnDef } from "@tanstack/react-table";
import { EllipsisVertical } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import type { RecentLeadRow } from "./schema";

export const recentLeadsColumns: ColumnDef<RecentLeadRow>[] = [
  {
    id: "select",
    header: ({ table }) => {
      const t = useTranslations("Legacy.CRM.table");
      return (
        <div className="flex items-center justify-center">
          <Checkbox
            checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")}
            onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
            aria-label={t("select_all")}
          />
        </div>
      );
    },
    cell: ({ row }) => {
      const t = useTranslations("Legacy.CRM.table");
      return (
        <div className="flex items-center justify-center">
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label={t("select_row")}
          />
        </div>
      );
    },
    enableHiding: false,
  },
  {
    accessorKey: "id",
    header: "Ref",
    cell: ({ row }) => <span className="">{row.original.id}</span>,
    enableHiding: false,
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => row.original.name,
    enableHiding: false,
  },
  {
    accessorKey: "company",
    header: "Company",
    cell: ({ row }) => row.original.company,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <Badge variant="secondary">{row.original.status}</Badge>,
  },
  {
    accessorKey: "source",
    header: "Source",
    cell: ({ row }) => <Badge variant="outline">{row.original.source}</Badge>,
  },
  {
    accessorKey: "lastActivity",
    header: "Last Activity",
    cell: ({ row }) => <span className="text-muted-foreground">{row.original.lastActivity}</span>,
  },
  {
    id: "actions",
    cell: () => {
      const t = useTranslations("Legacy.CRM.table");
      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="flex size-8 text-muted-foreground">
              <EllipsisVertical />
              <span className="sr-only">{t("open_menu")}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-32">
            <DropdownMenuGroup>
              <DropdownMenuItem>{t("actions.view")}</DropdownMenuItem>
              <DropdownMenuItem>{t("actions.assign")}</DropdownMenuItem>
              <DropdownMenuItem>{t("actions.archive")}</DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem variant="destructive">{t("actions.delete")}</DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
    enableHiding: false,
  },
];