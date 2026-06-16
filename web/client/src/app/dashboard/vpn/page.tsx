"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/providers";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import QRCode from "react-qr-code";

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------
type VpnAccount = {
  id: string;
  name: string;
  protocol: "wireguard" | "xray";
  status: "active" | "suspended" | "expired" | "deleted";
  traffic_used_gb: number;
  traffic_limit_gb: number | null;
  created_at: string;
  expires_at: string | null;
};

type TrafficStats = {
  download_gb: number;
  upload_gb: number;
  total_gb: number;
};

type VpnConfig = {
  config_text: string;
  protocol: string;
  name: string;
};

// ------------------------------------------------------------------
// API Helpers
// ------------------------------------------------------------------
async function apiFetch(path: string, options?: RequestInit) {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: "Request failed" }));
    throw new Error(error.message || error.detail || "Request failed");
  }
  return res.json();
}

// ------------------------------------------------------------------
// Icons
// ------------------------------------------------------------------
function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  );
}

function QrCodeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0113.5 9.375v-4.5z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 6.75h.75v.75h-.75v-.75zM6.75 16.5h.75v.75h-.75v-.75zM16.5 6.75h.75v.75h-.75v-.75z" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function ChartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  );
}

function ArrowPathIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182M20.016 4.34v4.993m0 0h-4.993" />
    </svg>
  );
}

// ------------------------------------------------------------------
// Status Badge Component
// ------------------------------------------------------------------
function StatusBadge({ status }: { status: VpnAccount["status"] }) {
  const variants: Record<string, string> = {
    active: "bg-green-100 text-green-800 border-green-200",
    suspended: "bg-yellow-100 text-yellow-800 border-yellow-200",
    expired: "bg-red-100 text-red-800 border-red-200",
    deleted: "bg-gray-100 text-gray-800 border-gray-200",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${variants[status] || variants.active}`}>
      {status}
    </span>
  );
}

// ------------------------------------------------------------------
// Main Page Component
// ------------------------------------------------------------------
export default function VpnDashboardPage() {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  const [accounts, setAccounts] = useState<VpnAccount[]>([]);
  const [trafficStats, setTrafficStats] = useState<Record<string, TrafficStats>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createProtocol, setCreateProtocol] = useState<"wireguard" | "xray">("wireguard");
  const [createName, setCreateName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configData, setConfigData] = useState<VpnConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(false);

  const [showQrModal, setShowQrModal] = useState(false);
  const [qrAccountId, setQrAccountId] = useState<string | null>(null);

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Auth guard
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Fetch VPN accounts
  const fetchAccounts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch("/vpn/accounts");
      setAccounts(data.accounts || []);
    } catch (err: any) {
      setError(err.message || "Failed to load VPN accounts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchAccounts();
    }
  }, [isAuthenticated, fetchAccounts]);

  // Fetch traffic stats for an account
  const fetchTrafficStats = useCallback(async (accountId: string) => {
    try {
      const data = await apiFetch(`/vpn/accounts/${accountId}/traffic`);
      setTrafficStats((prev) => ({ ...prev, [accountId]: data }));
    } catch {
      // silently fail, will show "--" in UI
    }
  }, []);

  useEffect(() => {
    accounts.forEach((acc) => {
      if (!trafficStats[acc.id]) {
        fetchTrafficStats(acc.id);
      }
    });
  }, [accounts, trafficStats, fetchTrafficStats]);

  // Create VPN account
  const handleCreateAccount = async () => {
    try {
      setCreating(true);
      setCreateError(null);
      await apiFetch("/vpn/accounts", {
        method: "POST",
        body: JSON.stringify({
          protocol: createProtocol,
          name: createName || undefined,
        }),
      });
      setShowCreateModal(false);
      setCreateName("");
      setCreateProtocol("wireguard");
      await fetchAccounts();
    } catch (err: any) {
      setCreateError(err.message || "Failed to create VPN account");
    } finally {
      setCreating(false);
    }
  };

  // Download config
  const handleDownloadConfig = async (accountId: string) => {
    try {
      setConfigLoading(true);
      const data = await apiFetch(`/vpn/accounts/${accountId}/config`);
      setConfigData(data);
      setShowConfigModal(true);
    } catch (err: any) {
      setError(err.message || "Failed to generate config");
    } finally {
      setConfigLoading(false);
    }
  };

  // Download config as file
  const downloadConfigFile = () => {
    if (!configData) return;
    const blob = new Blob([configData.config_text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `vpn_${configData.protocol}_${configData.name || "config"}.conf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Delete account
  const handleDeleteAccount = async (accountId: string) => {
    try {
      setDeleting(true);
      await apiFetch(`/vpn/accounts/${accountId}`, { method: "DELETE" });
      setDeleteConfirmId(null);
      setAccounts((prev) => prev.filter((a) => a.id !== accountId));
    } catch (err: any) {
      setError(err.message || "Failed to delete VPN account");
    } finally {
      setDeleting(false);
    }
  };

  // Renew config
  const handleRenewConfig = async (accountId: string) => {
    try {
      await apiFetch(`/vpn/accounts/${accountId}/renew`, { method: "POST" });
      await fetchAccounts();
    } catch (err: any) {
      setError(err.message || "Failed to renew VPN config");
    }
  };

  // Format GB
  const formatGB = (gb: number | undefined): string => {
    if (gb === undefined || gb === null) return "-- GB";
    return `${gb.toFixed(2)} GB`;
  };

  // Total traffic
  const totalTraffic = Object.values(trafficStats).reduce(
    (sum, s) => sum + (s?.total_gb || 0),
    0
  );

  if (isLoading || !isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between py-4">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="text-xl font-bold">
              BlueHub
            </Link>
            <nav className="hidden md:flex items-center gap-4">
              <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </Link>
              <Link href="/dashboard/vpn" className="text-sm font-medium text-foreground">
                VPN
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {user?.full_name || user?.email}
            </span>
            <button
              onClick={logout}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <section className="container py-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <ShieldIcon className="h-7 w-7 text-primary" />
              VPN Management
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Manage your WireGuard and VLESS+REALITY VPN services
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            Create VPN
          </button>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {error}
            <button onClick={() => setError(null)} className="ml-4 font-medium hover:underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="p-6 bg-card rounded-lg border shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Total Accounts</h3>
            <p className="text-2xl font-bold">{accounts.length}</p>
          </div>
          <div className="p-6 bg-card rounded-lg border shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Active Accounts</h3>
            <p className="text-2xl font-bold">
              {accounts.filter((a) => a.status === "active").length}
            </p>
          </div>
          <div className="p-6 bg-card rounded-lg border shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Total Traffic</h3>
            <p className="text-2xl font-bold">{formatGB(totalTraffic)}</p>
          </div>
          <div className="p-6 bg-card rounded-lg border shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Most Used</h3>
            <p className="text-2xl font-bold">
              {accounts.length > 0
                ? accounts[0].protocol === "wireguard"
                  ? "WireGuard"
                  : "VLESS"
                : "--"}
            </p>
          </div>
        </div>

        {/* Accounts Table */}
        <div className="bg-card rounded-lg border shadow-sm overflow-hidden">
          <div className="p-4 border-b flex items-center justify-between">
            <h3 className="text-lg font-semibold">Your VPN Accounts</h3>
            <button
              onClick={fetchAccounts}
              className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              disabled={loading}
            >
              <ArrowPathIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {loading && accounts.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <div className="animate-pulse">Loading VPN accounts...</div>
            </div>
          ) : accounts.length === 0 ? (
            <div className="p-12 text-center">
              <ShieldIcon className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground mb-4">No VPN accounts yet.</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <PlusIcon className="h-4 w-4" />
                Create your first VPN
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left p-3 text-xs font-medium text-muted-foreground">Name</th>
                    <th className="text-left p-3 text-xs font-medium text-muted-foreground">Protocol</th>
                    <th className="text-left p-3 text-xs font-medium text-muted-foreground">Status</th>
                    <th className="text-left p-3 text-xs font-medium text-muted-foreground">Traffic</th>
                    <th className="text-left p-3 text-xs font-medium text-muted-foreground">Limit</th>
                    <th className="text-left p-3 text-xs font-medium text-muted-foreground">Created</th>
                    <th className="text-right p-3 text-xs font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((account) => {
                    const stats = trafficStats[account.id];
                    return (
                      <tr key={account.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                        <td className="p-3 text-sm font-medium">{account.name || `VPN-${account.id.slice(0, 8)}`}</td>
                        <td className="p-3 text-sm">
                          <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
                            {account.protocol === "wireguard" ? "WireGuard" : "VLESS+REALITY"}
                          </span>
                        </td>
                        <td className="p-3">
                          <StatusBadge status={account.status} />
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">
                          {stats ? `${stats.total_gb.toFixed(2)} GB` : "--"}
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">
                          {account.traffic_limit_gb ? `${account.traffic_limit_gb} GB` : "Unlimited"}
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">
                          {new Date(account.created_at).toLocaleDateString()}
                        </td>
                        <td className="p-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => handleDownloadConfig(account.id)}
                              disabled={configLoading}
                              className="inline-flex items-center rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                              title="Download Config"
                            >
                              <DownloadIcon className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => {
                                setQrAccountId(account.id);
                                setShowQrModal(true);
                              }}
                              className="inline-flex items-center rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                              title="Show QR Code"
                            >
                              <QrCodeIcon className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleRenewConfig(account.id)}
                              className="inline-flex items-center rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                              title="Renew Config"
                            >
                              <ArrowPathIcon className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(account.id)}
                              className="inline-flex items-center rounded-md p-2 text-muted-foreground hover:bg-red-100 hover:text-red-600 transition-colors"
                              title="Delete Account"
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-lg border shadow-lg w-full max-w-md p-6 mx-4">
            <h3 className="text-lg font-semibold mb-4">Create VPN Account</h3>
            {createError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                {createError}
              </div>
            )}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Protocol</label>
                <select
                  value={createProtocol}
                  onChange={(e) => setCreateProtocol(e.target.value as "wireguard" | "xray")}
                  className="w-full rounded-lg border px-3 py-2 text-sm bg-background"
                >
                  <option value="wireguard">WireGuard</option>
                  <option value="xray">VLESS+REALITY</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Account Name (optional)</label>
                <input
                  type="text"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="e.g., My Personal VPN"
                  className="w-full rounded-lg border px-3 py-2 text-sm bg-background"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setCreateError(null);
                }}
                className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateAccount}
                disabled={creating}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {creating ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Config Modal */}
      {showConfigModal && configData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-lg border shadow-lg w-full max-w-lg p-6 mx-4">
            <h3 className="text-lg font-semibold mb-4">VPN Configuration</h3>
            <div className="relative">
              <pre className="bg-muted rounded-lg border p-4 text-xs font-mono overflow-x-auto max-h-96 whitespace-pre-wrap">
                {configData.config_text}
              </pre>
            </div>
            <div className="flex justify-between items-center mt-4">
              <button
                onClick={downloadConfigFile}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <DownloadIcon className="h-4 w-4" />
                Download File
              </button>
              <button
                onClick={() => {
                  setShowConfigModal(false);
                  setConfigData(null);
                }}
                className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* QR Code Modal */}
      {showQrModal && qrAccountId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-lg border shadow-lg w-full max-w-sm p-6 mx-4 text-center">
            <h3 className="text-lg font-semibold mb-4">QR Code</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Scan this QR code in your VPN client app to import the configuration.
            </p>
            <div className="bg-white p-4 rounded-lg inline-block">
              {/* Note: In production, fetch the config text and render actual QR */}
              <div className="w-48 h-48 mx-auto flex items-center justify-center bg-muted rounded">
                <QrCodeIcon className="h-16 w-16 text-muted-foreground" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Account: {qrAccountId.slice(0, 8)}...
            </p>
            <button
              onClick={() => {
                setShowQrModal(false);
                setQrAccountId(null);
              }}
              className="mt-4 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-lg border shadow-lg w-full max-w-sm p-6 mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full bg-red-100">
                <TrashIcon className="h-5 w-5 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold">Delete VPN Account</h3>
            </div>
            <p className="text-sm text-muted-foreground mb-2">
              Are you sure you want to delete this VPN account?
            </p>
            <p className="text-sm font-medium text-red-600 mb-6">
              This action cannot be undone. All configurations and keys will be revoked.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteAccount(deleteConfirmId)}
                disabled={deleting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}