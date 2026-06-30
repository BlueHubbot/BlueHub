"use client";

import { useEffect, useState } from "react";
import { adminApi, api } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";
import {
  Search,
  Filter,
  Download,
  ChevronDown,
  Clock,
  AlertCircle,
  Info,
  Ban,
  CheckCircle2,
  Loader2,
} from "lucide-react";

interface LogEntry {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string | number;
  actor_id: number;
  actor_name: string;
  tenant_id: number;
  ip_address: string;
  details: Record<string, unknown>;
  created_at: string;
}

interface LogsResponse {
  items: LogEntry[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

const ACTION_ICONS: Record<string, React.ReactNode> = {
  create: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  update: <Info className="h-4 w-4 text-blue-500" />,
  delete: <Ban className="h-4 w-4 text-red-500" />,
  login: <Info className="h-4 w-4 text-blue-500" />,
  suspend: <AlertCircle className="h-4 w-4 text-yellow-500" />,
  activate: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  terminate: <Ban className="h-4 w-4 text-red-500" />,
};

const ACTION_COLORS: Record<string, string> = {
  create: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  update: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  delete: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  login: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  suspend: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  activate: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  terminate: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [showFilters, setShowFilters] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadLogs();
  }, [page, actionFilter]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const params: Record<string, unknown> = {
        page,
        per_page: 20,
      };
      if (actionFilter !== "all") params.action = actionFilter;
      if (search) params.search = search;

      const response = await api.get<LogsResponse>("/admin/logs", { params });
      setLogs(response.data.items);
      setTotalPages(response.data.total_pages);
      setTotal(response.data.total);
    } catch (err) {
      setError("Failed to load logs");
      // Use demo data
      setLogs(generateDemoLogs());
      setTotalPages(5);
      setTotal(97);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    loadLogs();
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await api.get("/admin/logs/export", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      // Demo export
      toast.success("Logs exported successfully (demo)");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit Logs</h1>
          <p className="mt-1 text-muted-foreground">
            Track all system activities and changes
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="inline-flex items-center gap-2 rounded-lg border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
        >
          {exporting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Export
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800 dark:border-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200">
          {error} — showing demo data
        </div>
      )}

      {/* Filters */}
      <div className="rounded-xl border bg-card shadow-sm">
        <div className="p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search logs..."
                className="w-full rounded-lg border border-input bg-background pl-10 pr-4 py-2 text-sm placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>

            {/* Filter Toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center gap-2 rounded-lg border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
            >
              <Filter className="h-4 w-4" />
              Filters
              <ChevronDown
                className={`h-4 w-4 transition-transform ${
                  showFilters ? "rotate-180" : ""
                }`}
              />
            </button>
          </div>

          {/* Expandable Filters */}
          {showFilters && (
            <div className="mt-4 flex flex-wrap gap-3 pt-4 border-t">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Action:</span>
                <select
                  value={actionFilter}
                  onChange={(e) => {
                    setActionFilter(e.target.value);
                    setPage(1);
                  }}
                  className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="all">All Actions</option>
                  <option value="create">Create</option>
                  <option value="update">Update</option>
                  <option value="delete">Delete</option>
                  <option value="login">Login</option>
                  <option value="suspend">Suspend</option>
                  <option value="activate">Activate</option>
                  <option value="terminate">Terminate</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Clock className="h-4 w-4" />
        <span>
          {total} log entries found
          {loading && " (loading...)"}
        </span>
      </div>

      {/* Logs Table */}
      <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Actor</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Entity</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Details</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">IP</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-muted/50 transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          ACTION_COLORS[log.action] ||
                          "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400"
                        }`}
                      >
                        {ACTION_ICONS[log.action] || <Info className="h-3 w-3" />}
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-sm font-medium">{log.actor_name}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-sm text-muted-foreground">
                        {log.entity_type}
                      </span>
                      <span className="ml-1 text-xs text-muted-foreground/60">
                        #{log.entity_id}
                      </span>
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <p className="text-sm text-muted-foreground truncate">
                        {JSON.stringify(log.details) || "-"}
                      </p>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <code className="text-xs text-muted-foreground">
                        {log.ip_address}
                      </code>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-muted-foreground">
                      {formatRelativeTime(log.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Empty State */}
        {!loading && logs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Search className="h-12 w-12 text-muted-foreground/40" />
            <h3 className="mt-4 text-lg font-medium">No logs found</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Try adjusting your search or filters
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper toast for demo
const toast = {
  success: (msg: string) => {
    // In real app, use sonner
    console.log("SUCCESS:", msg);
  },
};

function generateDemoLogs(): LogEntry[] {
  const actions = ["create", "update", "delete", "login", "suspend", "activate", "terminate"];
  const entityTypes = ["user", "service", "product", "tenant", "module"];
  const actors = ["admin@bluehub.com", "operator@bluehub.com", "system"];
  const ips = ["192.168.1.1", "10.0.0.1", "45.33.32.156", "8.8.8.8"];

  return Array.from({ length: 20 }, (_, i) => ({
    id: 1000 - i,
    action: actions[Math.floor(Math.random() * actions.length)],
    entity_type: entityTypes[Math.floor(Math.random() * entityTypes.length)],
    entity_id: Math.floor(Math.random() * 500) + 1,
    actor_id: Math.floor(Math.random() * 10) + 1,
    actor_name: actors[Math.floor(Math.random() * actors.length)],
    tenant_id: 1,
    ip_address: ips[Math.floor(Math.random() * ips.length)],
    details: { description: "Sample log entry for demo purposes" },
    created_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
  }));
}