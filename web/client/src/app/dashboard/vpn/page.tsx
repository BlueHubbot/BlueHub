"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/providers";
import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
  BarChart,
  Bar,
} from "recharts";
import { Shield, Zap, BarChart3, Users, Radio, ArrowDown, ArrowUp, Download, QrCode, Trash2, Plus, RefreshCw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
// API Helper
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
// Format GB helper
// ------------------------------------------------------------------
function formatGB(gb: number | undefined | null): string {
  if (gb === undefined || gb === null) return "-- GB";
  return `${gb.toFixed(2)} GB`;
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

  // ─── Computed Values ───────────────────────
  const activeCount = useMemo(
    () => accounts.filter((a) => a.status === "active").length,
    [accounts]
  );
  const suspendedCount = useMemo(
    () => accounts.filter((a) => a.status === "suspended").length,
    [accounts]
  );
  const totalDownload = useMemo(
    () => Object.values(trafficStats).reduce((s, t) => s + (t?.download_gb || 0), 0),
    [trafficStats]
  );
  const totalUpload = useMemo(
    () => Object.values(trafficStats).reduce((s, t) => s + (t?.upload_gb || 0), 0),
    [trafficStats]
  );
  const totalTraffic = totalDownload + totalUpload;

  const wireguardCount = useMemo(
    () => accounts.filter((a) => a.protocol === "wireguard").length,
    [accounts]
  );
  const xrayCount = useMemo(
    () => accounts.filter((a) => a.protocol === "xray").length,
    [accounts]
  );

  // Per-account traffic data for bar chart
  const perAccountTrafficData = useMemo(() => {
    return accounts
      .map((a) => ({
        name: a.name || a.id.slice(0, 8),
        download: trafficStats[a.id]?.download_gb || 0,
        upload: trafficStats[a.id]?.upload_gb || 0,
      }))
      .filter((d) => d.download > 0 || d.upload > 0)
      .slice(0, 10);
  }, [accounts, trafficStats]);

  // Protocol distribution data for pie-like bar chart
  const protocolTrafficData = useMemo(() => {
    const wgTraffic = accounts
      .filter((a) => a.protocol === "wireguard")
      .reduce((s, a) => s + (trafficStats[a.id]?.total_gb || 0), 0);
    const xrTraffic = accounts
      .filter((a) => a.protocol === "xray")
      .reduce((s, a) => s + (trafficStats[a.id]?.total_gb || 0), 0);
    return [
      { name: "WireGuard", traffic: wgTraffic },
      { name: "VLESS/Xray", traffic: xrTraffic },
    ].filter((d) => d.traffic > 0);
  }, [accounts, trafficStats]);

  // ─── Render Helpers ────────────────────────
  const renderChartPlaceholder = () => (
    <div className="flex flex-col items-center justify-center py-12 h-72 text-muted-foreground">
      <BarChart3 className="w-10 h-10 mb-2 opacity-30" />
      <p className="text-sm">No traffic data yet</p>
    </div>
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
      <header className="border-b sticky top-0 bg-background/95 backdrop-blur z-40">
        <div className="container flex h-16 items-center justify-between py-4">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="text-xl font-bold tracking-tight">
              BlueHub
            </Link>
            <nav className="hidden md:flex items-center gap-1">
              <Link
                href="/dashboard"
                className="text-sm px-3 py-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                Dashboard
              </Link>
              <Link
                href="/dashboard/vpn"
                className="text-sm px-3 py-1.5 rounded-md font-medium bg-muted text-foreground"
              >
                VPN
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {user?.full_name || user?.email}
            </span>
            <Button variant="ghost" size="sm" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <section className="container py-8 space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Shield className="h-7 w-7 text-primary" />
              VPN Management
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Manage your WireGuard and VLESS+REALITY VPN services
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchAccounts}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="h-4 w-4 mr-1" />
              Create VPN
            </Button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm">
            {error}
            <Button
              variant="link"
              size="sm"
              onClick={() => setError(null)}
              className="ml-2"
            >
              Dismiss
            </Button>
          </div>
        )}

        {/* ─── Stats Cards ─────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Users className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Accounts</p>
                  <p className="text-2xl font-bold">{accounts.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/10">
                  <Zap className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Active</p>
                  <p className="text-2xl font-bold">{activeCount}</p>
                  {suspendedCount > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {suspendedCount} suspended
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <BarChart3 className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Traffic</p>
                  <p className="text-2xl font-bold">{formatGB(totalTraffic)}</p>
                  <div className="flex gap-2 text-xs text-muted-foreground mt-0.5">
                    <span className="flex items-center gap-0.5">
                      <ArrowDown className="h-3 w-3" />
                      {totalDownload.toFixed(1)} GB
                    </span>
                    <span className="flex items-center gap-0.5">
                      <ArrowUp className="h-3 w-3" />
                      {totalUpload.toFixed(1)} GB
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <Radio className="h-5 w-5 text-purple-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Protocols</p>
                  <p className="text-2xl font-bold">{wireguardCount + xrayCount}</p>
                  <p className="text-xs text-muted-foreground">
                    {wireguardCount} WG · {xrayCount} Xray
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ─── Traffic Charts ───────────────────── */}
        {accounts.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Per-Account Traffic Bar Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Traffic by Account</CardTitle>
                <CardDescription>Total transfer per VPN account</CardDescription>
              </CardHeader>
              <CardContent>
                {perAccountTrafficData.length === 0 ? (
                  renderChartPlaceholder()
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={perAccountTrafficData}
                        layout="vertical"
                        margin={{ top: 5, right: 20, left: 40, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                        <XAxis
                          type="number"
                          tick={{ fontSize: 11 }}
                          stroke="hsl(var(--muted-foreground))"
                          tickFormatter={(v: number) => `${v.toFixed(1)}`}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          tick={{ fontSize: 11 }}
                          stroke="hsl(var(--muted-foreground))"
                          width={80}
                        />
                        <Tooltip
                          formatter={(value: number) => [`${value.toFixed(2)} GB`, undefined]}
                          contentStyle={{
                            background: "hsl(var(--card))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "8px",
                          }}
                        />
                        <Legend />
                        <Bar
                          dataKey="download"
                          name="Download"
                          stackId="a"
                          fill="hsl(var(--primary))"
                          radius={[0, 0, 4, 4]}
                        />
                        <Bar
                          dataKey="upload"
                          name="Upload"
                          stackId="a"
                          fill="hsl(var(--chart-2, 210 50% 60%))"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Protocol Distribution Bar Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Protocol Distribution</CardTitle>
                <CardDescription>Traffic split by protocol type</CardDescription>
              </CardHeader>
              <CardContent>
                {protocolTrafficData.length === 0 ? (
                  renderChartPlaceholder()
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={protocolTrafficData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis
                          dataKey="name"
                          tick={{ fontSize: 11 }}
                          stroke="hsl(var(--muted-foreground))"
                        />
                        <YAxis
                          tick={{ fontSize: 11 }}
                          stroke="hsl(var(--muted-foreground))"
                          tickFormatter={(v: number) => `${v.toFixed(1)} GB`}
                        />
                        <Tooltip
                          formatter={(value: number) => [`${value.toFixed(2)} GB`, "Traffic"]}
                          contentStyle={{
                            background: "hsl(var(--card))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "8px",
                          }}
                        />
                        <Bar
                          dataKey="traffic"
                          name="Total Traffic"
                          radius={[4, 4, 0, 0]}
                          fill="hsl(var(--primary))"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* ─── Accounts Table ────────────────────── */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Your VPN Accounts</CardTitle>
                <CardDescription>{accounts.length} account(s) total</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading && accounts.length === 0 ? (
              <div className="space-y-3 py-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : accounts.length === 0 ? (
              <div className="py-12 text-center">
                <Shield className="mx-auto h-12 w-12 text-muted-foreground/30 mb-4" />
                <p className="text-muted-foreground mb-4">No VPN accounts yet</p>
                <Button onClick={() => setShowCreateModal(true)}>
                  <Plus className="h-4 w-4 mr-1" />
                  Create Your First VPN
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
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
                        <tr
                          key={account.id}
                          className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                        >
                          <td className="p-3 text-sm font-medium">
                            {account.name || `VPN-${account.id.slice(0, 8)}`}
                          </td>
                          <td className="p-3">
                            <Badge variant="outline" className="text-xs">
                              {account.protocol === "wireguard" ? "WireGuard" : "VLESS+REALITY"}
                            </Badge>
                          </td>
                          <td className="p-3">
                            <Badge
                              variant={
                                account.status === "active"
                                  ? "default"
                                  : account.status === "suspended"
                                  ? "secondary"
                                  : "destructive"
                              }
                              className="text-xs"
                            >
                              {account.status}
                            </Badge>
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
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => handleDownloadConfig(account.id)}
                                disabled={configLoading}
                                title="Download Config"
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => {
                                  setQrAccountId(account.id);
                                  setShowQrModal(true);
                                }}
                                title="Show QR Code"
                              >
                                <QrCode className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => handleRenewConfig(account.id)}
                                title="Renew Config"
                              >
                                <RefreshCw className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 hover:text-destructive"
                                onClick={() => setDeleteConfirmId(account.id)}
                                title="Delete Account"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* ─── Create Modal ──────────────────────── */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create VPN Account</DialogTitle>
            <DialogDescription>
              Choose a protocol and optionally name your account
            </DialogDescription>
          </DialogHeader>
          {createError && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              {createError}
            </div>
          )}
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Protocol</label>
              <select
                value={createProtocol}
                onChange={(e) => setCreateProtocol(e.target.value as "wireguard" | "xray")}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="wireguard">WireGuard</option>
                <option value="xray">VLESS+REALITY</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Account Name (optional)</label>
              <input
                type="text"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="e.g., My Personal VPN"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateModal(false);
                setCreateError(null);
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleCreateAccount} disabled={creating}>
              {creating ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Config Modal ──────────────────────── */}
      <Dialog open={showConfigModal} onOpenChange={setShowConfigModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>VPN Configuration</DialogTitle>
            <DialogDescription>
              Copy or download this configuration file
            </DialogDescription>
          </DialogHeader>
          <div className="relative">
            <pre className="bg-muted rounded-lg border p-4 text-xs font-mono overflow-x-auto max-h-96 whitespace-pre-wrap">
              {configData?.config_text}
            </pre>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowConfigModal(false);
                setConfigData(null);
              }}
            >
              Close
            </Button>
            <Button onClick={downloadConfigFile} disabled={!configData}>
              <Download className="h-4 w-4 mr-1" />
              Download File
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── QR Code Modal ─────────────────────── */}
      <Dialog open={showQrModal} onOpenChange={setShowQrModal}>
        <DialogContent className="max-w-sm text-center">
          <DialogHeader>
            <DialogTitle>QR Code</DialogTitle>
            <DialogDescription>
              Scan this QR code in your VPN client app to import the configuration
            </DialogDescription>
          </DialogHeader>
          <div className="bg-white p-4 rounded-lg inline-block mx-auto">
            <div className="w-48 h-48 mx-auto flex items-center justify-center bg-muted rounded">
              <QrCode className="h-16 w-16 text-muted-foreground" />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Account: {qrAccountId?.slice(0, 8)}...
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowQrModal(false);
                setQrAccountId(null);
              }}
              className="w-full"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Delete Confirmation Modal ──────────── */}
      <Dialog
        open={!!deleteConfirmId}
        onOpenChange={(open) => {
          if (!open) setDeleteConfirmId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-destructive" />
              Delete VPN Account
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this VPN account? This action cannot be undone. All
              configurations and keys will be revoked.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirmId && handleDeleteAccount(deleteConfirmId)}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}