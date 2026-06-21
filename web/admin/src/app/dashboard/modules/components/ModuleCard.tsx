"use client";

import type { ModuleRegistryEntry, ModuleTogglePayload } from "@/lib/api";
import {
  Power,
  PowerOff,
  Settings,
  AlertTriangle,
  StopCircle,
  Wrench,
  ChevronDown,
  ChevronUp,
  Blocks,
  Package,
  Globe,
  Tv,
  Gamepad2,
  Server,
} from "lucide-react";
import { useState } from "react";

interface ModuleCardProps {
  module: ModuleRegistryEntry;
  toggling: string | null;
  onToggle: (field: keyof ModuleTogglePayload, value: boolean) => void;
  onConfigure: () => void;
}

const MODULE_ICONS: Record<string, typeof Blocks> = {
  vpn: Globe,
  vps: Server,
  smartdns: Tv,
  streaming: Tv,
  game: Gamepad2,
};

const MODULE_COLORS: Record<
  string,
  { bg: string; text: string; border: string }
> = {
  vpn: {
    bg: "bg-blue-50 dark:bg-blue-950/30",
    text: "text-blue-600 dark:text-blue-400",
    border: "border-blue-200 dark:border-blue-800",
  },
  vps: {
    bg: "bg-green-50 dark:bg-green-950/30",
    text: "text-green-600 dark:text-green-400",
    border: "border-green-200 dark:border-green-800",
  },
  smartdns: {
    bg: "bg-purple-50 dark:bg-purple-950/30",
    text: "text-purple-600 dark:text-purple-400",
    border: "border-purple-200 dark:border-purple-800",
  },
  streaming: {
    bg: "bg-pink-50 dark:bg-pink-950/30",
    text: "text-pink-600 dark:text-pink-400",
    border: "border-pink-200 dark:border-pink-800",
  },
  game: {
    bg: "bg-orange-50 dark:bg-orange-950/30",
    text: "text-orange-600 dark:text-orange-400",
    border: "border-orange-200 dark:border-orange-800",
  },
};

const DEFAULT_COLOR = {
  bg: "bg-gray-50 dark:bg-gray-950/30",
  text: "text-gray-600 dark:text-gray-400",
  border: "border-gray-200 dark:border-gray-800",
};

export function ModuleCard({ module: mod, toggling, onToggle, onConfigure }: ModuleCardProps) {
  const [expanded, setExpanded] = useState(false);
  const Icon = MODULE_ICONS[mod.module_name] || Package;
  const colors = MODULE_COLORS[mod.module_name] || DEFAULT_COLOR;
  const isToggling = toggling === mod.module_name;
  const hasFlags =
    mod.flags.stop_new_sales ||
    mod.flags.terminate_services ||
    mod.flags.maintenance_mode;

  return (
    <div
      className={`rounded-lg border bg-card text-card-foreground shadow-sm transition-all hover:shadow-md ${
        !mod.enabled ? "opacity-60" : ""
      } ${hasFlags ? "ring-2 ring-yellow-400/50" : ""}`}
    >
      {/* Card Header */}
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`rounded-lg p-2.5 ${colors.bg} ${colors.border} border`}>
              <Icon className={`h-5 w-5 ${colors.text}`} />
            </div>
            <div>
              <h3 className="font-semibold">{mod.display_name}</h3>
              <p className="text-xs text-muted-foreground font-mono">
                v{mod.version}
              </p>
            </div>
          </div>

          {/* Status indicator */}
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                mod.enabled
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  mod.enabled ? "bg-green-500" : "bg-gray-400"
                }`}
              />
              {mod.enabled ? "Active" : "Disabled"}
            </span>
          </div>
        </div>

        {/* Description */}
        {mod.description && (
          <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
            {mod.description}
          </p>
        )}

        {/* Flags */}
        {hasFlags && (
          <div className="mt-3 flex flex-wrap gap-2">
            {mod.flags.stop_new_sales && (
              <span className="inline-flex items-center gap-1 rounded-md bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                <StopCircle className="h-3 w-3" />
                Stop New Sales
              </span>
            )}
            {mod.flags.terminate_services && (
              <span className="inline-flex items-center gap-1 rounded-md bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
                <PowerOff className="h-3 w-3" />
                Terminate Services
              </span>
            )}
            {mod.flags.maintenance_mode && (
              <span className="inline-flex items-center gap-1 rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                <Wrench className="h-3 w-3" />
                Maintenance
              </span>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between border-t px-5 py-3">
        {/* Toggle enable/disable */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => onToggle("enabled", !mod.enabled)}
            disabled={isToggling}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              mod.enabled
                ? "bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-950/30 dark:text-red-400 dark:hover:bg-red-950/50"
                : "bg-green-50 text-green-600 hover:bg-green-100 dark:bg-green-950/30 dark:text-green-400 dark:hover:bg-green-950/50"
            } disabled:opacity-50`}
            title={mod.enabled ? "Disable module" : "Enable module"}
          >
            {isToggling ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : mod.enabled ? (
              <PowerOff className="h-3.5 w-3.5" />
            ) : (
              <Power className="h-3.5 w-3.5" />
            )}
            {mod.enabled ? "Disable" : "Enable"}
          </button>

          {/* Quick flag toggles */}
          {mod.enabled && (
            <>
              {!mod.flags.stop_new_sales && (
                <button
                  onClick={() => onToggle("stop_new_sales", true)}
                  disabled={isToggling}
                  className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-yellow-600 hover:bg-yellow-50 dark:text-yellow-400 dark:hover:bg-yellow-950/30 disabled:opacity-50"
                  title="Stop new sales"
                >
                  <StopCircle className="h-3.5 w-3.5" />
                  Stop Sales
                </button>
              )}
              {!mod.flags.maintenance_mode && (
                <button
                  onClick={() => onToggle("maintenance_mode", true)}
                  disabled={isToggling}
                  className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950/30 disabled:opacity-50"
                  title="Maintenance mode"
                >
                  <Wrench className="h-3.5 w-3.5" />
                  Maintenance
                </button>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* Configure */}
          <button
            onClick={onConfigure}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent disabled:opacity-50"
            title="Module configuration"
          >
            <Settings className="h-3.5 w-3.5" />
            Config
          </button>

          {/* Expand info */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent"
          >
            {expanded ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t px-5 py-3 space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Module Name</span>
            <span className="font-mono">{mod.module_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Order</span>
            <span>{mod.order}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Flags</span>
            <span className="font-mono">
              {mod.flags.stop_new_sales ? "SNS " : ""}
              {mod.flags.terminate_services ? "TERM " : ""}
              {mod.flags.maintenance_mode ? "MAINT" : ""}
              {!hasFlags ? "none" : ""}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Has Config Schema</span>
            <span>{mod.config_schema ? "Yes" : "No"}</span>
          </div>
        </div>
      )}
    </div>
  );
}