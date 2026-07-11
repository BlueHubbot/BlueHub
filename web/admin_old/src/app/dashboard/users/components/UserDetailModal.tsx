"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import {
  X,
  Loader2,
  Server,
  Activity,
  Globe,
  Shield,
  Monitor,
  Clock,
  Wifi,
} from "lucide-react";
import type { UserData, ServiceData, AuditLogEntry } from "../page";

interface UserDetailModalProps {
  user: UserData;
  onClose: () => void;
}

const SERVICE_ICONS: Record<string, React.ReactNode> = {
  vpn: <Shield className="h-4 w-4" />,
  vps: <Server className="h-4 w-4" />,
  streaming: <Monitor className="h-4 w-4" />,
  smartdns: <Globe className="h-4 w-4" />,
  game: <Activity className="h-4 w-4" />,
};

const SERVICE_LABELS: Record<string, string> = {
  vpn: "VPN",
  vps: "VPS",
  streaming: "Streaming",
  smartdns: "Smart DNS",
  game: "Game Server",
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500",
  suspended: "bg-red-500",
  expired: "bg-yellow-500",
  pending: "bg-blue-500",
  cancelled: "bg-gray-500",
};

type Tab = "services" | "audit";

export function UserDetailModal({ user, onClose }: UserDetailModalProps) {
  const [tab, setTab] = useState<Tab>("services");
  const [services, setServices] = useState<ServiceData[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loadingServices, setLoadingServices] = useState(true);
  const [loadingAudit, setLoadingAudit] = useState(true);
  const [servicesError, setServicesError] = useState<string | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);

  const fetchServices = useCallback(async () => {
    if (tab !== "services") return;
    try {
      setServicesError(null);
      setLoadingServices(true);
      const res = await api.get<ServiceData[]>(`/admin/users/${user.id}/services`);
      setServices(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load services";
      setServicesError(msg);
    } finally {
      setLoadingServices(false);
    }
  }, [user.id, tab]);

  const fetchAuditLogs = useCallback(async () => {
    if (tab !== "audit") return;
    try {
      setAuditError(null);
      setLoadingAudit(true);
      const res = await api.get<AuditLogEntry[]>(`/admin/users/${user.id}/audit-logs`);
      setAuditLogs(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load audit logs";
      setAuditError(msg);
    } finally {
      setLoadingAudit(false);
    }
  }, [user.id, tab]);

  useEffect(() => {
    if (tab === "services") fetchServices();
    if (tab === "audit") fetchAuditLogs();
  }, [tab, fetchServices, fetchAuditLogs]);

  const getStatusLabel = (s: string) => {
    return s.charAt(0).toUpperCase() + s.slice(1);
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-hidden rounded-xl border bg-card shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4 shrink-0">
          <div>
            <h2 className="text-xl font-bold">{user.username || user.email}</h2>
            <p className="text-sm text-muted-foreground">{user.email}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* User info bar */}
        <div className="flex flex-wrap gap-4 border-b bg-muted/20 px-6 py-3 text-xs text-muted-foreground shrink-0">
          <span>
            <span className="font-medium">Role:</span>{" "}
            <span className="capitalize">{user.role}</span>
          </span>
          <span>
            <span className="font-medium">Status:</span>{" "}
            {user.suspended ? (
              <span className="text-red-500 font-medium">Suspended</span>
            ) : user.active ? (
              <span className="text-green-500 font-medium">Active</span>
            ) : (
              <span className="text-gray-500 font-medium">Inactive</span>
            )}
          </span>
          {user.telegram_id && (
            <span>
              <span className="font-medium">Telegram:</span>{" "}
              <code className="font-mono">{user.telegram_id}</code>
            </span>
          )}
          <span>
            <span className="font-medium">Language:</span> {user.language || "en"}
          </span>
          {user.tenant_name && (
            <span>
              <span className="font-medium">Tenant:</span> {user.tenant_name}
            </span>
          )}
          <span>
            <span className="font-medium">Joined:</span>{" "}
            {user.created_at ? formatDate(user.created_at) : "—"}
          </span>
        </div>

        {/* Tabs */}
        <div className="flex border-b px-6 shrink-0">
          <button
            onClick={() => setTab("services")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === "services"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Server className="h-4 w-4" />
            Services
          </button>
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
          {/* Services tab */}
          {tab === "services" && (
            <>
              {loadingServices && (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              )}

              {servicesError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
                  <p>{servicesError}</p>
                </div>
              )}

              {!loadingServices && !servicesError && services.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Wifi className="h-10 w-10 text-muted-foreground/50" />
                  <h3 className="mt-3 text-lg font-medium">No services</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    This user has no active or past services.
                  </p>
                </div>
              )}

              {!loadingServices && !servicesError && services.length > 0 && (
                <div className="space-y-3">
                  {services.map((svc) => (
                    <div
                      key={svc.id}
                      className="flex items-center justify-between rounded-lg border p-4 hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="rounded-md bg-muted p-2 text-muted-foreground">
                          {SERVICE_ICONS[svc.type] || <Server className="h-4 w-4" />}
                        </div>
                        <div>
                          <p className="font-medium text-sm">
                            {svc.name || SERVICE_LABELS[svc.type] || svc.type}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span
                              className={`inline-block h-2 w-2 rounded-full ${
                                STATUS_COLORS[svc.status] || "bg-gray-400"
                              }`}
                            />
                            <span className="text-xs text-muted-foreground capitalize">
                              {getStatusLabel(svc.status)}
                            </span>
                            <span className="text-xs text-muted-foreground">•</span>
                            <span className="text-xs text-muted-foreground">
                              <Clock className="h-3 w-3 inline-block mr-0.5" />
                              {formatDate(svc.created_at)}
                            </span>
                          </div>
                        </div>
                      </div>
                      <code className="rounded bg-muted px-2 py-1 text-xs font-mono">
                        {svc.id.slice(0, 12)}...
                      </code>
                    </div>
                  ))}
                </div>
              )}
            </>
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
                    No audit history found for this user.
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
                          <code className="text-[11px]">{log.ip_address}</code>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}