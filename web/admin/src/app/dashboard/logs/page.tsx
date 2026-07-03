"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
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
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | number;
  user_id: string;
  user_email?: string;
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
      const searchParams = new URLSearchParams();
      searchParams.set("page", String(page));
      searchParams.set("per_page", "20");
      if (search) searchParams.set("search", search);
      if (actionFilter !== "all") searchParams.set("action", actionFilter);

      const response = await api.get<LogsResponse>(`/admin/logs?${searchParams.toString()}`);
      setLogs(response.data.items || []);
      setTotalPages(response.data.total_pages || 1);
      setTotal(response.data.total || 0);
      setError(null);
    } catch (err) {
      setError("Failed to load logs");
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
      const data = await api.get("/admin/logs/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Audit Logs</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track all system activities and changes
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="inline-flex items-center gap-2 rounded-lg border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
        >
          {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          Export
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800 dark:border-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200">
          {error} — showing demo data
        </div>
      )}

      <div className="rounded-xl border bg-card shadow-sm">
        <div className="p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
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
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center gap-2 rounded-lg border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
            >
              <Filter className="h-4 w-4" />
              Filters
              <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? "rotate-180" : ""}`} />
            </button>
          </div>

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

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Clock className="h-4 w-4" />
        <span>{total} log entries found{loading && " (loading...)"}</span>
      </div>

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
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Entity</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Details</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">IP</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        ACTION_COLORS[log.action] || "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400"
                      }`}>
                        {ACTION_ICONS[log.action] || <Info className="h-3 w-3" />}
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-sm font-medium">{log.user_email || log.user_id || "System"}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-sm text-muted-foreground">{log.entity_type}</span>
                      <span className="ml-1 text-xs text-muted-foreground/60">#{log.entity_id}</span>
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <p className="text-sm text-muted-foreground truncate">
                        {typeof log.details === "object" ? JSON.stringify(log.details).slice(0, 50) : String(log.details)}
                      </p>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <code className="text-xs text-muted-foreground">{log.ip_address || "-"}</code>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-muted-foreground">
                      {formatDate(log.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && logs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Search className="h-12 w-12 text-muted-foreground/40" />
            <h3 className="mt-4 text-lg font-medium">No logs found</h3>
            <p className="mt-1 text-sm text-muted-foreground">Try adjusting your search or filters</p>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">Page {page} of {totalPages}</p>
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

function generateDemoLogs(): LogEntry[] {
  const actions = ["create", "update", "delete", "login", "suspend", "activate", "terminate"];
  const entityTypes = ["user", "service", "product", "tenant", "module"];
  const users = ["admin@bluehub.com", "operator@bluehub.com", "system"];
  const ips = ["192.168.1.1", "10.0.0.1", "45.33.32.156", "8.8.8.8"];

  return Array.from({ length: 20 }, (_, i) => ({
    id: `log-${1000 - i}`,
    action: actions[Math.floor(Math.random() * actions.length)],
    entity_type: entityTypes[Math.floor(Math.random() * entityTypes.length)],
    entity_id: Math.floor(Math.random() * 500) + 1,
    user_id: `user-${Math.floor(Math.random() * 10) + 1}`,
    user_email: users[Math.floor(Math.random() * users.length)],
    ip_address: ips[Math.floor(Math.random() * ips.length)],
    details: { description: "Sample log entry for demo purposes" },
    created_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
  }));
}