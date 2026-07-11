"use client";
"use no memo";

import * as React from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { addMinutes, differenceInCalendarDays, endOfToday, format, parseISO } from "date-fns";
import { CircleAlertIcon, CircleCheckIcon, Clock3Icon, LoaderIcon, UserRound } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";

import type { RecentCustomerRow } from "./schema";

const getBillingConfig = (billing: string, t: any) => {
  const configs: Record<string, { icon: React.ReactNode; label: string }> = {
    Paid: { icon: <CircleCheckIcon className="fill-green-500 stroke-primary-foreground dark:fill-green-600" />, label: t('paid') },
    Pending: { icon: <LoaderIcon />, label: t('pending') },
    Overdue: { icon: <CircleAlertIcon className="text-amber-600 dark:text-amber-500" />, label: t('overdue') },
    Trial: { icon: <Clock3Icon className="text-muted-foreground" />, label: t('trial') },
  };
  return configs[billing] || { icon: null, label: billing };
};

export const getColumns = (t: any): ColumnDef<RecentCustomerRow>[] => [
  {
    id: "select",
    header: ({ table }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      </div>
    ),
    cell: ({ row }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      </div>
    ),
    enableHiding: false,
  },
  {
    accessorKey: "name",
    header: t('customer'),
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-md border bg-muted">
          <UserRound className="size-4 text-muted-foreground" />
        </span>
        <div className="grid gap-0.5">
          <span className="font-medium text-sm">{row.original.name}</span>
          <span className="text-muted-foreground text-xs">#{row.original.id}</span>
        </div>
      </div>
    ),
  },
  {
    accessorKey: "plan",
    header: t('plan'),
    cell: ({ row }) => <span className="text-sm">{row.original.plan}</span>,
  },
  {
    accessorKey: "billing",
    header: t('billing'),
    cell: ({ row }) => {
      const config = getBillingConfig(row.original.billing, t);
      return (
        <Badge variant="outline" className="flex w-fit items-center gap-1 px-1.5 text-muted-foreground">
          {config.icon}
          {config.label}
        </Badge>
      );
    },
  },
  {
    accessorKey: "status",
    header: t('status'),
    cell: ({ row }) => (
      <Badge variant="outline" className="px-1.5 text-muted-foreground">
        {t(row.original.status.toLowerCase())}
      </Badge>
    ),
  },
  {
    accessorKey: "joined",
    header: t('joined'),
    cell: ({ row }) => {
      const baseDate = parseISO(row.original.joined);
      const joinedAt = addMinutes(baseDate, 9 * 60 + (Number(row.original.id) % 12) * 17);
      return (
        <div className="grid gap-0.5">
          <span className="text-sm">{format(joinedAt, "dd MMMM yyyy")}</span>
          <span className="text-muted-foreground text-xs">{t('at')} {format(joinedAt, "h:mm a")}</span>
        </div>
      );
    },
  },
];