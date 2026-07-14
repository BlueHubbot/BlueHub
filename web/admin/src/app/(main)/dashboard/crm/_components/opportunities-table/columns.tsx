"use client";
"use no memo";

import * as React from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Pencil } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

import type { OpportunityRow } from "./schema";

const healthStripSlots = Array.from({ length: 18 }, (_, index) => ({
  id: `strip-${index + 1}`,
  threshold: index + 1,
}));

function getHealthScore(health: OpportunityRow["health"]) {
  switch (health) {
    case "On Track":
      return 18;
    case "Needs Review":
      return 11;
    case "At Risk":
      return 7;
    case "On Hold":
      return 4;
    default:
      return 0;
  }
}

export const getOpportunitiesColumns = (t: any): ColumnDef<OpportunityRow>[] => [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")}
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label={t('select_all_opportunities')}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label={t('select_opportunity', { account: row.original.account })}
      />
    ),
    enableHiding: false,
  },
  {
    id: "actions",
    header: () => <div className="text-right">{t('edit')}</div>,
    cell: () => (
      <div className="text-right">
        <Button
          variant="ghost"
          size="icon"
          className="size-8 rounded-full text-muted-foreground hover:bg-transparent focus-visible:bg-transparent"
        >
          <Pencil className="size-4" />
          <span className="sr-only">{t('edit_opportunity')}</span>
        </Button>
      </div>
    ),
    enableHiding: false,
  },
  {
    accessorKey: "account",
    header: t('account'),
    cell: ({ row }) => <div className="font-medium text-sm">{row.original.account}</div>,
  },
  {
    accessorKey: "stage",
    header: t('stage'),
    cell: ({ row }) => {
      const stageKey = String(row.original.stage).toLowerCase().replace(/\s+/g, '_');
      return (
        <Badge variant="outline" className="rounded-full px-2.5">
          {t.has(stageKey) ? t(stageKey) : row.original.stage}
        </Badge>
      );
    },
    filterFn: "equalsString",
  },
  {
    accessorKey: "priority",
    header: t('priority'),
    cell: ({ row }) => <div className="text-sm ">{String(row.original.priority)}</div>,
  },
  {
    accessorKey: "health",
    header: t('health'),
    cell: ({ row }) => (
      <div className="flex items-end gap-0.5" title={t(row.original.health.toLowerCase().replace(/\s+/g, '_'))}>
        <span className="sr-only">{t(row.original.health.toLowerCase().replace(/\s+/g, '_'))}</span>
        {healthStripSlots.map((slot) => (
          <div
            key={`${row.original.id}-${slot.id}`}
            className={cn(
              "h-5 w-1 rounded-full",
              slot.threshold <= getHealthScore(row.original.health) ? "bg-green-500/85" : "bg-green-500/15",
            )}
          />
        ))}
      </div>
    ),
    filterFn: "equalsString",
  },
  {
    accessorKey: "value",
    header: t('value'),
    cell: ({ row }) => <div className="font-medium text-sm ">{row.original.value}</div>,
  },
  {
    accessorKey: "id",
    header: t('id'),
    cell: ({ row }) => <div className="text-sm tracking-tight">{row.original.id}</div>,
    enableHiding: false,
  },
];