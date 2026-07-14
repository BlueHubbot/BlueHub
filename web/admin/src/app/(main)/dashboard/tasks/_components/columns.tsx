"use client";

import type { Column, ColumnDef } from "@tanstack/react-table";
import { useTranslations } from "next-intl";
import { ArrowDown, ArrowUp, ArrowUpDown, MoreHorizontal, RotateCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

import { labels, priorities, statuses, type Task } from "./data";

const statusStyles: Record<string, string> = {
  backlog: "border-muted-foreground/20 bg-muted text-muted-foreground",
  todo: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  "in progress": "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  done: "border-green-500/20 bg-green-500/10 text-green-700 dark:text-green-300",
  canceled: "border-muted-foreground/20 bg-muted text-muted-foreground",
};

function SortIcon({ sortDirection }: { sortDirection: false | "asc" | "desc" }) {
  if (sortDirection === "desc") {
    return <ArrowDown data-icon="inline-end" />;
  }
  if (sortDirection === "asc") {
    return <ArrowUp data-icon="inline-end" />;
  }
  return <ArrowUpDown data-icon="inline-end" />;
}

function TitleColumnHeader({ column }: { column: Column<Task, unknown> }) {
  const t = useTranslations("Tasks");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="-ml-3 text-muted-foreground data-[state=open]:bg-accent">
          {t("title")}
          <SortIcon sortDirection={column.getIsSorted()} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuItem onSelect={() => column.toggleSorting(false)}>
          <ArrowUp />
          {t("asc")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => column.toggleSorting(true)}>
          <ArrowDown />
          {t("desc")}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => column.clearSorting()}>
          <RotateCcw />
          {t("reset")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export const columns: ColumnDef<Task>[] = [
  {
    id: "select",
    header: ({ table }) => {
      const t = useTranslations("Tasks");
      return (
        <Checkbox
          checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label={t("select_all")}
          className="translate-y-0.5"
        />
      );
    },
    cell: ({ row }) => {
      const t = useTranslations("Tasks");
      return (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label={t("select_row")}
          className="translate-y-0.5"
        />
      );
    },
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "id",
    header: () => {
      const t = useTranslations("Tasks");
      return t("task");
    },
    cell: ({ row }) => <div className="w-20 font-mono text-muted-foreground text-sm">{row.getValue("id")}</div>,
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "title",
    header: ({ column }) => <TitleColumnHeader column={column} />,
    cell: ({ row }) => {
      const t = useTranslations("Tasks");
      const label = labels.find((l) => l.value === row.original.label);

      return (
        <div className="flex min-w-0 items-center gap-2">
          {label && (
            <Badge className="rounded-sm bg-transparent" variant="outline">
              {t(`labels.${label.value}`)}
            </Badge>
          )}
          <span className="max-w-lg truncate font-medium text-sm">{row.getValue("title")}</span>
        </div>
      );
    },
  },
  {
    accessorKey: "status",
    header: () => {
      const t = useTranslations("Tasks");
      return t("status");
    },
    cell: ({ row }) => {
      const t = useTranslations("Tasks");
      const status = statuses.find((s) => s.value === row.getValue("status"));

      if (!status) return null;

      return (
        <Badge className={cn("gap-1.5 rounded-sm border font-medium", statusStyles[status.value])} variant="outline">
          {status.icon && <status.icon className="size-4" />}
          {t(`statuses.${status.value.replace(/\s/g, "_")}`)}
        </Badge>
      );
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id));
    },
  },
  {
    accessorKey: "priority",
    header: () => {
      const t = useTranslations("Tasks");
      return t("priority");
    },
    cell: ({ row }) => {
      const t = useTranslations("Tasks");
      const priority = priorities.find((p) => p.value === row.getValue("priority"));

      if (!priority) return null;

      return (
        <div className="flex items-center gap-2 text-sm">
          {priority.icon && <priority.icon className="size-4 text-muted-foreground" />}
          {t(`priorities.${priority.value}`)}
        </div>
      );
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id));
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const t = useTranslations("Tasks");
      const task = row.original as Task;

      return (
        <div className="text-right">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" className="text-muted-foreground data-[state=open]:bg-muted">
                <MoreHorizontal />
                <span className="sr-only">{t("open_menu")}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuItem>{t("actions.edit")}</DropdownMenuItem>
              <DropdownMenuItem>{t("actions.make_copy")}</DropdownMenuItem>
              <DropdownMenuItem>{t("actions.favorite")}</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuSub>
                <DropdownMenuSubTrigger>{t("actions.labels")}</DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  <DropdownMenuRadioGroup value={task.label}>
                    {labels.map((label) => (
                      <DropdownMenuRadioItem key={label.value} value={label.value}>
                        {t(`labels.${label.value}`)}
                      </DropdownMenuRadioItem>
                    ))}
                  </DropdownMenuRadioGroup>
                </DropdownMenuSubContent>
              </DropdownMenuSub>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                {t("actions.delete")}
                <DropdownMenuShortcut>⌘⌫</DropdownMenuShortcut>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      );
    },
  },
];