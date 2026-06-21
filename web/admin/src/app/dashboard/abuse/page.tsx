"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getUser } from "@/lib/auth";
import {
  Search,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Ban,
  ChevronLeft,
  ChevronRight,
  Eye,
  RotateCcw,
} from "lucide-react";
import { AbuseDetailModal } from "./components/AbuseDetailModal";
import { AbuseResolveModal } from "./components/AbuseResolveModal";

export interface AbuseReport {
  id: string;
  user_id: string;
  user_email?: string;
  user_username?: string;
  reporter_id?: string;
  reporter_email?: string;
  reporter_username?: string;
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "open" | "investigating" | "resolved" | "dismissed";
  description: string;
  evidence?: string;
  ip_address?: string;
  service_id?: string;
  service_type?: string;
  auto_detected: boolean;
  resolved_by?: string;
  resolution_notes?: string;
  created_at: string;
  updated_at?: string;
  resolved_at?: string;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  details: string;
  ip_address: string;
  created_at: string;
}

interface PaginationData {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

const severityColors: Record<string, string> = {
  low: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  medium: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  high: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  critical: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
};

const statusColors: Record<string, string> = {
  open: "bg-red-500",
  investigating: "bg-blue-500",
  resolved: "bg-green-500",
  dismissed: "bg-gray-400",
};

const statusBadgeColors: Record<string, string> = {
  open: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  investigating: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  resolved: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  dismissed: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
};

const reportTypeLabels: Record<string, string> = {
  spam: "Spam",
  phishing: "Phishing",
  abuse: "Abuse",
  copyright: "Copyright Infringement",
  impersonation: "Impersonation",
  malware: "Malware",
  policy_violation: "Policy Violation",
  bandwidth_abuse: "Bandwidth Abuse",
  port_scan: "Port Scanning",
  ddos: "DDoS Activity",
  other: "Other",
};

export default function AbusePage() {
  const router = useRouter();
  const user = getUser();
  const [reports, setReports] = useState<AbuseReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");
  const [filterType, setFilterType] = useState("");

  // Pagination
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<PaginationData>({
    total: 0,
    page: 1,
    per_page: 100,
    pages: 1,
  });

  // Modal state
  const [detailReport, setDetailReport] = useState<AbuseReport | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [resolvingReport, setResolvingReport] = useState<AbuseReport | null>(null);
  const [resolveModalOpen, setResolveModalOpen] = useState(false);

  // Action loading states
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (filterStatus) params.set("status", filterStatus);
      if (filterSeverity) params.set("severity", filterSeverity);
      if (filterType) params.set("type", filterType);
      params.set("page", String(page));
      params.set("per_page", "100");

      const res = await api.get<{ reports: AbuseReport[]; pagination: PaginationData }>(
        `/admin/abuse-reports?${params.toString()}`
      );
      setReports(res.data.reports);
      setPagination(res.data.pagination);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load abuse reports";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [search, filterStatus, filterSeverity, filterType, page]);

  useEffect(() => {
    if (!user || !["admin", "superadmin"].includes(user.role)) {
      router.push("/login");
      return;
    }
    fetchReports();
  }, [user, router, fetchReports]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [search, filterStatus, filterSeverity, filterType]);

  const handleStatusChange = async (report: AbuseReport, newStatus: string) => {
    try {
      setProcessingId(report.id);
      setError(null);
      await api.patch(`/admin/abuse-reports/${report.id}`, {
        status: newStatus,
      });
      await fetchReports();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update report status";
      setError(msg);
    } finally {
      setProcessingId(null);
    }
  };

  const handleResolved = () => {
    setResolveModalOpen(false);
    setResolvingReport(null);
    fetchReports();
  };

  const getSeverityBadge = (severity: string) => (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${severityColors[severity] || "bg-gray-100 text-gray-800"}`}>
      {severity}
    </span>
  );

  const getStatusBadge = (status: string) => (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadgeColors[status] || "bg-gray-100 text-gray-800"}`}>
      {status}
    </span>
  );

  const statsSummary = {
    open: reports.filter((r) => r.status === "open").length,
    investigating: reports.filter((r) => r.status === "investigating").length,
    critical: reports.filter((r) => r.severity === "critical" && r.status !== "resolved" && r.status !== "dismissed").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Abuse Reports</h1>
          <p className="text-sm text-muted-foreground">
            Monitor and manage platform abuse reports, security incidents, and policy violations.
          </p>
        </div>
        <p className="text-sm text-muted-foreground">
          {pagination.total} report{pagination.total !== 1 && "s"}
        </p>
      </div>

      {/* Summary stats */}
      {(statsSummary.open > 0 || statsSummary.investigating > 0 || statsSummary.critical > 0) && (
        <div className="flex flex-wrap gap-4">
          {statsSummary.open > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 dark:border-red-800 dark:bg-red-950">
              <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
              <span className="text-sm font-medium text-red-700 dark:text-red-300">
                {statsSummary.open} open report{statsSummary.open !== 1 && "s"}
              </span>
            </div>
          )}
          {statsSummary.investigating > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 dark:border-blue-800 dark:bg-blue-950">
              <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                {statsSummary.investigating} under investigation
              </span>
            </div>
          )}
          {statsSummary.critical > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-purple-200 bg-purple-50 px-4 py-2 dark:border-purple-800 dark:bg-purple-950">
              <Ban className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
                {statsSummary.critical} unresolved critical
              </span>
            </div>
          )}
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          <p>{error}</p>
          <button onClick={() => setError(null)} className="mt-1 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[250px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by reporter, user, or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border bg-background py-2 pl-10 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="investigating">Investigating</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All Severities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All Types</option>
          {Object.entries(reportTypeLabels).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {/* Empty state */}
      {!loading && reports.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <CheckCircle2 className="h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No reports found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {search || filterStatus || filterSeverity || filterType
              ? "Try different filters."
              : "No abuse reports to review. The platform is running smoothly."}
          </p>
        </div>
      )}

      {/* Reports table */}
      {!loading && reports.length > 0 && (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Reporter</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Target User</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Severity</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Auto</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">IP</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Reported</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {reports.map((report) => (
                <tr
                  key={report.id}
                  className={`group hover:bg-muted/30 transition-colors ${
                    report.status === "resolved" || report.status === "dismissed" ? "opacity-60" : ""
                  }`}
                >
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="font-medium">{report.reporter_username || report.reporter_email || "System"}</span>
                      {report.reporter_email && (
                        <span className="text-xs text-muted-foreground">{report.reporter_email}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="font-medium">{report.user_username || report.user_email || "—"}</span>
                      {report.user_email && (
                        <span className="text-xs text-muted-foreground">{report.user_email}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium">
                      {reportTypeLabels[report.type] || report.type}
                    </span>
                  </td>
                  <td className="px-4 py-3">{getSeverityBadge(report.severity)}</td>
                  <td className="px-4 py-3">{getStatusBadge(report.status)}</td>
                  <td className="px-4 py-3">
                    {report.auto_detected ? (
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                        Auto
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">Manual</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {report.ip_address ? (
                      <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                        {report.ip_address}
                      </code>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                    {report.created_at
                      ? new Date(report.created_at).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {/* View detail */}
                      <button
                        onClick={() => {
                          setDetailReport(report);
                          setDetailModalOpen(true);
                        }}
                        className="rounded-md p-1.5 text-muted-foreground hover:bg-muted transition-colors"
                        title="View details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>

                      {/* Quick actions based on status */}
                      {report.status === "open" && (
                        <button
                          onClick={() => handleStatusChange(report, "investigating")}
                          disabled={processingId === report.id}
                          className="inline-flex items-center gap-1 rounded-md border border-blue-200 px-2.5 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 transition-colors disabled:opacity-50 dark:border-blue-800 dark:text-blue-400 dark:hover:bg-blue-950"
                        >
                          {processingId === report.id ? (
                            <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                          ) : (
                            <Clock className="h-3.5 w-3.5" />
                          )}
                          Investigate
                        </button>
                      )}
                      {report.status === "investigating" && (
                        <>
                          <button
                            onClick={() => {
                              setResolvingReport(report);
                              setResolveModalOpen(true);
                            }}
                            className="inline-flex items-center gap-1 rounded-md border border-green-200 px-2.5 py-1 text-xs font-medium text-green-600 hover:bg-green-50 transition-colors dark:border-green-800 dark:text-green-400 dark:hover:bg-green-950"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Resolve
                          </button>
                          <button
                            onClick={() => handleStatusChange(report, "dismissed")}
                            disabled={processingId === report.id}
                            className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-900"
                          >
                            {processingId === report.id ? (
                              <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                            ) : (
                              <XCircle className="h-3.5 w-3.5" />
                            )}
                            Dismiss
                          </button>
                        </>
                      )}
                      {(report.status === "resolved" || report.status === "dismissed") && (
                        <button
                          onClick={() => handleStatusChange(report, "open")}
                          disabled={processingId === report.id}
                          className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium hover:bg-muted transition-colors disabled:opacity-50"
                        >
                          {processingId === report.id ? (
                            <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                          ) : (
                            <RotateCcw className="h-3.5 w-3.5" />
                          )}
                          Reopen
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {!loading && pagination.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {pagination.page} of {pagination.pages} ({pagination.total} reports)
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            {Array.from({ length: pagination.pages }, (_, i) => i + 1)
              .filter((p) => {
                return (
                  p === 1 ||
                  p === pagination.pages ||
                  Math.abs(p - page) <= 2
                );
              })
              .map((p, idx, arr) => (
                <span key={p} className="flex items-center">
                  {idx > 0 && arr[idx - 1] !== p - 1 && (
                    <span className="px-1 text-muted-foreground">...</span>
                  )}
                  <button
                    onClick={() => setPage(p)}
                    className={`min-w-[36px] rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      p === page
                        ? "bg-primary text-primary-foreground border-primary"
                        : "hover:bg-muted"
                    }`}
                  >
                    {p}
                  </button>
                </span>
              ))}
            <button
              onClick={() => setPage((p) => Math.min(pagination.pages, p + 1))}
              disabled={page >= pagination.pages}
              className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {detailModalOpen && detailReport && (
        <AbuseDetailModal
          report={detailReport}
          onClose={() => {
            setDetailModalOpen(false);
            setDetailReport(null);
          }}
          onStatusChange={(newStatus: string) => {
            handleStatusChange(detailReport, newStatus);
            setDetailModalOpen(false);
            setDetailReport(null);
          }}
        />
      )}

      {/* Resolve Modal */}
      {resolveModalOpen && resolvingReport && (
        <AbuseResolveModal
          report={resolvingReport}
          onResolved={handleResolved}
          onClose={() => {
            setResolveModalOpen(false);
            setResolvingReport(null);
          }}
        />
      )}
    </div>
  );
}