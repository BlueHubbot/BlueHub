"use client";

import { useEffect, useState, useCallback } from "react";
import { adminApi, type ModuleRegistryEntry, type ModuleTogglePayload } from "@/lib/api";
import { useAdminAuth } from "@/lib/auth";
import { ModuleCard } from "./components/ModuleCard";
import { DisableConfirmModal } from "./components/DisableConfirmModal";
import { ModuleConfigModal } from "./components/ModuleConfigModal";
import { RefreshCw, AlertCircle, Search } from "lucide-react";

type SortField = "order" | "name" | "status";
type SortDir = "asc" | "desc";

export default function ModulesPage() {
  const { user } = useAdminAuth();
  const [modules, setModules] = useState<ModuleRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("order");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Modals
  const [disableTarget, setDisableTarget] = useState<ModuleRegistryEntry | null>(null);
  const [configTarget, setConfigTarget] = useState<ModuleRegistryEntry | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);

  const loadModules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getModules();
      setModules(res.data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load modules";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadModules();
  }, [loadModules]);

  // ── Toggle handlers ──────────────────────────────────────────────────

  const handleToggle = async (
    mod: ModuleRegistryEntry,
    field: keyof ModuleTogglePayload,
    value: boolean
  ) => {
    // If disabling module, show confirmation modal
    if (field === "enabled" && !value) {
      setDisableTarget(mod);
      return;
    }
    await doToggle(mod.module_name, { [field]: value });
  };

  const doToggle = async (name: string, payload: ModuleTogglePayload) => {
    setToggling(name);
    try {
      const res = await adminApi.updateModule(name, payload);
      setModules((prev) =>
        prev.map((m) => (m.module_name === name ? res.data : m))
      );
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to update module";
      setError(message);
    } finally {
      setToggling(null);
    }
  };

  const handleDisableConfirm = async () => {
    if (!disableTarget) return;
    await doToggle(disableTarget.module_name, { enabled: false });
    setDisableTarget(null);
  };

  // ── Sorting & Filtering ──────────────────────────────────────────────

  const filtered = modules
    .filter(
      (m) =>
        m.module_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (m.description || "").toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      let cmp = 0;
      if (sortField === "order") cmp = (a.order ?? 0) - (b.order ?? 0);
      else if (sortField === "name")
        cmp = a.display_name.localeCompare(b.display_name);
      else if (sortField === "status")
        cmp = Number(a.enabled) - Number(b.enabled);
      return sortDir === "asc" ? cmp : -cmp;
    });

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const activeCount = modules.filter((m) => m.enabled).length;
  const flaggedCount = modules.filter(
    (m) =>
      m.flags.stop_new_sales ||
      m.flags.terminate_services ||
      m.flags.maintenance_mode
  ).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Module Management</h1>
          <p className="mt-1 text-muted-foreground">
            Enable, disable, and configure service modules
          </p>
        </div>
        <button
          onClick={loadModules}
          className="btn-secondary flex items-center gap-2"
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Summary bar */}
      <div className="flex flex-wrap gap-4 text-sm">
        <div className="rounded-lg border bg-card px-4 py-2">
          <span className="text-muted-foreground">Total: </span>
          <span className="font-semibold">{modules.length}</span>
        </div>
        <div className="rounded-lg border bg-card px-4 py-2">
          <span className="text-muted-foreground">Active: </span>
          <span className="font-semibold text-green-600">{activeCount}</span>
        </div>
        <div className="rounded-lg border bg-card px-4 py-2">
          <span className="text-muted-foreground">Flagged: </span>
          <span
            className={`font-semibold ${
              flaggedCount > 0 ? "text-yellow-600" : ""
            }`}
          >
            {flaggedCount}
          </span>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/30 dark:text-red-200">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-600 hover:text-red-800 dark:text-red-400"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Search & Sort */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search modules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field pl-9 w-full"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Sort:</span>
          {(["order", "name", "status"] as const).map((field) => (
            <button
              key={field}
              onClick={() => toggleSort(field)}
              className={`btn-sm ${
                sortField === field ? "btn-primary" : "btn-secondary"
              }`}
            >
              {field === "order" ? "Order" : field === "name" ? "Name" : "Status"}
              {sortField === field && (
                <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Module Grid */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          {searchQuery
            ? "No modules match your search."
            : "No modules found. The module registry may need to be initialized."}
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((mod) => (
            <ModuleCard
              key={mod.module_name}
              module={mod}
              toggling={toggling}
              onToggle={(field: keyof ModuleTogglePayload, value: boolean) => handleToggle(mod, field, value)}
              onConfigure={() => setConfigTarget(mod)}
            />
          ))}
        </div>
      )}

      {/* Disable Confirmation Modal */}
      <DisableConfirmModal
        module={disableTarget}
        onConfirm={handleDisableConfirm}
        onCancel={() => setDisableTarget(null)}
        loading={toggling === disableTarget?.module_name}
      />

      {/* Configuration Modal */}
      <ModuleConfigModal
        module={configTarget}
        onClose={() => setConfigTarget(null)}
        onSave={async (name: string, data: ModuleTogglePayload) => {
          await doToggle(name, data);
          setConfigTarget(null);
        }}
      />
    </div>
  );
}