"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import {
  X,
  Loader2,
  AlertTriangle,
  Clock,
  Activity,
  Shield,
  Globe,
  User,
  Ban,
  Copy,
  CheckCircle2,
  RotateCcw,
} from "lucide-react";
import type { AbuseReport, AuditLogEntry } from "../page";

interface AbuseDetailModalProps {
  report: AbuseReport;
  onClose: () => void;
  onStatusChange: (newStatus: string) => void;
}

const severityColors: Record<string, string> = {
  low: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  medium: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  high: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  critical: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
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

const severityScores: Record<string, number> = {
  low: 1,
  medium: 3,
  high: 7,
  critical: 10,
};

type Tab = "details" | "evidence" | "audit";

export function AbuseDetailModal({ report, onClose, onStatusChange }: AbuseDetailModalProps) {
  const [tab, setTab] = useState<Tab>("details");
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchAuditLogs = useCallback(async () => {
    if (tab !== "audit") return;
    try {
      setAuditError(null);
      setLoadingAudit(true);
      const res = await api.get<AuditLogEntry[]>(`/admin/abuse-reports/${report.id}/audit-logs`);
      setAuditLogs(res.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load audit logs";
      setAuditError(msg);
    } finally {
      setLoadingAudit(false);
    }
  }, [report.id, tab]);

  useEffect(() => {
    if (tab === "audit") fetchAuditLogs();
  }, [tab, fetchAuditLogs]);

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  const getTimeSince = (dateStr: string) => {
    try {
      const diff = Date.now() - new Date(dateStr).getTime();
      const hours = Math.floor(diff / 3600000);
      if (hours < 1) return "Less than an hour ago";
      if (hours < 24) return `${hours}h ago`;
      const days = Math.floor(hours / 24);
      if (days < 30) return `${days}d ago`;
      const months = Math.floor(days / 30);
      return `${months}mo ago`;
    } catch {
      return "";
    }
  };

  const handleCopyId = () => {
    navigator.clipboard.writeText(report.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const severityScore = severityScores[report.severity] || 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-hidden rounded-xl border bg-card shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className={`rounded-full p-2 ${
              report.severity === "critical"
                ? "bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-300"
                : report.severity === "high"
                ? "bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-300"
                : "bg-orange-100 text-orange-600 dark:bg-orange-900 dark:text-orange-300"
            }`}>
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold">
                {reportTypeLabels[report.type] || report.type}
              </h2>
              <p className="text-sm text-muted-foreground">
                Report #{report.id.slice(0, 8)}
                <button
                  onClick={handleCopyId}
                  className="ml-1 inline-flex items-center text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  {copied ? "Copied!" : <Copy className="h-3 w-3" />}
                </button>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Report info bar */}
        <div className="flex flex-wrap gap-x-4 gap-y-1.5 border-b bg-muted/20 px-6 py-3 text-xs text-muted-foreground shrink-0">
          <span>
            <span className="font-medium">Status:</span>{" "}
            <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${statusBadgeColors[report.status]}`}>
              {report.status}
            </span>
          </span>
          <span>
            <span className="font-medium">Severity:</span>{" "}
            <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${severityColors[report.severity]}`}>
              {report.severity}
            </span>
          </span>
          <span>
            <span className="font-medium">Score:</span>{" "}
            <span className={`font-mono ${
              severityScore >= 7 ? "text-red-500" : severityScore >= 3 ? "text-orange-500" : "text-yellow-500"
            }`}>
              {severityScore}/10
            </span>
          </span>
          {report.auto_detected && (
            <span>
              <span className="font-medium">Detection:</span>{" "}
              <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[11px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                Automated
              </span>
            </span>
          )}
          <span>
            <span className="font-medium">Reported:</span>{" "}
            {formatDate(report.created_at)}
          </span>
          {report.resolved_at && (
            <span>
              <span className="font-medium">Resolved:</span>{" "}
              {formatDate(report.resolved_at)}
            </span>
          )}
          {report.ip_address && (
            <span>
              <span className="font-medium">Source IP:</span>{" "}
              <code className="font-mono">{report.ip_address}</code>
            </span>
          )}
        </div>

        {/* Tabs */}
        <div className="flex border-b px-6 shrink-0">
          <button
            onClick={() => setTab("details")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === "details"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Shield className="h-4 w-4" />
            Details
          </button>
          {report.evidence && (
            <button
              onClick={() => setTab("evidence")}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === "evidence"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Ban className="h-4 w-4" />
              Evidence
            </button>
          )}
          <button
            onClick={() => setTab("audit")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === "audit"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Activity className="h-4 w-4" />
            Audit Logs
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Details tab */}
          {tab === "details" && (
            <div className="space-y-6">
              {/* Description */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-2">Description</h3>
                <div className="rounded-lg border bg-muted/20 p-4 text-sm">
                  <p className="whitespace-pre-wrap leading-relaxed">
                    {report.description || "No description provided."}
                  </p>
                </div>
              </div>

              {/* Reporter & Target */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Reporter */}
                <div className="rounded-lg border p-4">
                  <h3 className="text-xs font-medium text-muted-foreground mb-3 flex items-center gap-1.5">
                    <User className="h-3.5 w-3.5" />
                    Reporter
                  </h3>
                  {report.reporter_username || report.reporter_email ? (
                    <div className="space-y-1">
                      {report.reporter_username && (
                        <p className="text-sm font-medium">{report.reporter_username}</p>
                      )}
                      {report.reporter_email && (
                        <p className="text-xs text-muted-foreground">{report.reporter_email}</p>
                      )}
                      {report.reporter_id && (
                        <code className="text-[11px] text-muted-foreground font-mono">
                          ID: {report.reporter_id.slice(0, 12)}...
                        </code>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {report.auto_detected ? "Automated detection system" : "Anonymous"}
                    </p>
                  )}
                </div>

                {/* Target User */}
                <div className="rounded-lg border p-4">
                  <h3 className="text-xs font-medium text-muted-foreground mb-3 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Target User
                  </h3>
                  {report.user_username || report.user_email ? (
                    <div className="space-y-1">
                      {report.user_username && (
                        <p className="text-sm font-medium">{report.user_username}</p>
                      )}
                      {report.user_email && (
                        <p className="text-xs text-muted-foreground">{report.user_email}</p>
                      )}
                      {report.user_id && (
                        <code className="text-[11px] text-muted-foreground font-mono">
                          ID: {report.user_id.slice(0, 12)}...
                        </code>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Unknown</p>
                  )}
                </div>
              </div>

              {/* Service info */}
              {(report.service_id || report.service_type) && (
                <div className="rounded-lg border p-4">
                  <h3 className="text-xs font-medium text-muted-foreground mb-3 flex items-center gap-1.5">
                    <Globe className="h-3.5 w-3.5" />
                    Related Service
                  </h3>
                  <div className="space-y-1">
                    {report.service_type && (
                      <p className="text-sm">
                        <span className="text-muted-foreground">Type:</span>{" "}
                        <span className="font-medium capitalize">{report.service_type}</span>
                      </p>
                    )}
                    {report.service_id && (
                      <code className="text-[11px] text-muted-foreground font-mono">
                        Service ID: {report.service_id}
                      </code>
                    )}
                  </div>
                </div>
              )}

              {/* Resolution info */}
              {report.status === "resolved" && report.resolved_by && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950">
                  <h3 className="text-xs font-medium text-green-700 dark:text-green-300 mb-1">
                    Resolution
                  </h3>
                  <p className="text-sm text-green-800 dark:text-green-200">
                    Resolved by <span className="font-medium">{report.resolved_by}</span>
                    {report.resolved_at && (
                      <> on {formatDate(report.resolved_at)}</>
                    )}
                  </p>
                  {report.resolution_notes && (
                    <p className="mt-2 text-sm text-green-800/80 dark:text-green-200/80 whitespace-pre-wrap">
                      {report.resolution_notes}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Evidence tab */}
          {tab === "evidence" && report.evidence && (
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-muted-foreground">Supporting Evidence</h3>
              <div className="rounded-lg border bg-muted/20 p-4">
                <pre className="whitespace-pre-wrap text-sm font-mono leading-relaxed">
                  {report.evidence}
                </pre>
              </div>
            </div>
          )}

          {/* Audit logs tab */}
          {tab === "audit" && (
            <>
              {loadingAudit && (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              )}

              {auditError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
                  <p>{auditError}</p>
                </div>
              )}

              {!loadingAudit && !auditError && auditLogs.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Activity className="h-10 w-10 text-muted-foreground/50" />
                  <h3 className="mt-3 text-lg font-medium">No audit logs</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    No audit trail found for this report.
                  </p>
                </div>
              )}

              {!loadingAudit && !auditError && auditLogs.length > 0 && (
                <div className="space-y-2">
                  {auditLogs.map((log) => (
                    <div
                      key={log.id}
                      className="rounded-lg border p-4 hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <p className="text-sm font-medium">{log.action}</p>
                          <p className="text-xs text-muted-foreground">
                            {log.details}
                          </p>
                        </div>
                        <div className="text-right text-xs text-muted-foreground shrink-0 ml-4">
                          <p className="whitespace-nowrap">
                            {formatDate(log.created_at)}
                          </p>
                          {log.ip_address && (
                            <code className="text-[11px]">{log.ip_address}</code>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between border-t px-6 py-4 shrink-0">
          <p className="text-xs text-muted-foreground">
            {getTimeSince(report.created_at)} &middot;{" "}
            {report.auto_detected ? "Auto-detected" : "User-reported"}
          </p>
          <div className="flex items-center gap-2">
            {report.status === "open" && (
              <button
                onClick={() => {
                  setProcessing(true);
                  onStatusChange("investigating");
                }}
                disabled={processing}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {processing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Clock className="h-4 w-4" />
                )}
                Start Investigation
              </button>
            )}
            {report.status === "investigating" && (
              <>
                <button
                  onClick={() => {
                    setProcessing(true);
                    onStatusChange("dismissed");
                  }}
                  disabled={processing}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
                >
                  {processing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <X className="h-4 w-4" />
                  )}
                  Dismiss
                </button>
                <button
                  onClick={() => {
                    onClose();
                  }}
                  className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Resolve
                </button>
              </>
            )}
            {(report.status === "resolved" || report.status === "dismissed") && (
              <button
                onClick={() => {
                  setProcessing(true);
                  onStatusChange("open");
                }}
                disabled={processing}
                className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
              >
                {processing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RotateCcw className="h-4 w-4" />
                )}
                Reopen Report
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}