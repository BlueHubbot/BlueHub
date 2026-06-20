"use client";

import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Download,
  Shield,
  Zap,
  Globe,
  Server,
  Wifi,
  Clock,
  Power,
  PowerOff,
  Copy,
  Check,
  Loader2,
  AlertTriangle,
  Signal,
  BarChart3,
} from "lucide-react";
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
} from "recharts";
import {
  useVpnAccount,
  useVpnTraffic,
  useVpnConfig,
  useSuspendVpnAccount,
  useUnsuspendVpnAccount,
} from "@/lib/hooks/use-vpn";
import {
  formatTrafficBytes,
  statusLabel,
  protocolLabel,
  type VpnProtocol,
  type VpnTrafficResponse,
} from "@/lib/types/vpn";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

// ─── Status Badge Variant ────────────────────────
const statusVariant: Record<string, BadgeProps["variant"]> = {
  active: "default",
  suspended: "secondary",
  expired: "destructive",
  terminated: "destructive",
  provisioning: "outline",
  error: "destructive",
};

const protocolIcons: Record<VpnProtocol, React.ReactNode> = {
  wireguard: <Zap className="w-4 h-4" />,
  xray: <Shield className="w-4 h-4" />,
  vless: <Globe className="w-4 h-4" />,
  trojan: <Server className="w-4 h-4" />,
};

// ─── Time Range Toggle ────────────────────────────
type TimeRange = "1h" | "6h" | "24h" | "7d" | "30d";
const timeRanges: { key: TimeRange; label: string }[] = [
  { key: "1h", label: "1H" },
  { key: "6h", label: "6H" },
  { key: "24h", label: "24H" },
  { key: "7d", label: "7D" },
  { key: "30d", label: "30D" },
];

// ─── Mock Traffic Points Generator (replace with real API data) ─
function generateMockTrafficData(traffic: VpnTrafficResponse, points: number) {
  const now = Date.now();
  const totalBytes = traffic.usage.total_bytes;
  // Generate realistic-looking cumulative growth
  return Array.from({ length: points }, (_, i) => {
    const t = now - (points - i) * (60_000 * (points > 24 ? 60 : 5)); // 5min or 1h intervals
    const fraction = (i + 1) / points;
    const noise = (Math.random() - 0.5) * 0.1; // ±5% noise
    const cumulative = Math.max(0, totalBytes * (fraction + noise));
    return {
      time: new Date(t).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        ...(points > 24 ? { month: "short", day: "numeric" } : {}),
      }),
      timestamp: t,
      sent: cumulative * 0.55, // ~55% sent
      received: cumulative * 0.45, // ~45% received
      total: cumulative,
    };
  });
}

export default function VpnServiceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const accountId = params.id;

  const { data: account, isLoading, error } = useVpnAccount(accountId);
  const { data: traffic } = useVpnTraffic(accountId);
  const { data: config } = useVpnConfig(accountId, true);
  const suspendMut = useSuspendVpnAccount();
  const unsuspendMut = useUnsuspendVpnAccount();

  const [timeRange, setTimeRange] = useState<TimeRange>("24h");
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [showSuspendDialog, setShowSuspendDialog] = useState(false);
  const [copied, setCopied] = useState(false);
  const [suspendReason, setSuspendReason] = useState("");

  const pointsByRange: Record<TimeRange, number> = {
    "1h": 12,
    "6h": 24,
    "24h": 48,
    "7d": 7 * 24,
    "30d": 30,
  };

  const chartData = useMemo(() => {
    if (!traffic) return [];
    return generateMockTrafficData(traffic, pointsByRange[timeRange]);
  }, [traffic, timeRange]);

  const handleCopyConfig = () => {
    if (config?.config_text) {
      navigator.clipboard.writeText(config.config_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // ─── Loading State ─────────────────────
  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-5xl space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
    );
  }

  // ─── Error State ───────────────────────
  if (error || !account) {
    const detail =
      (error as any)?.response?.data?.detail ||
      (error as Error)?.message ||
      "Service not found";
    return (
      <div className="container mx-auto py-8 px-4 max-w-5xl">
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{detail}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  const usagePct = traffic?.usage.bandwidth_used_percent ?? 0;

  return (
    <div className="container mx-auto py-8 px-4 max-w-5xl space-y-6">
      {/* Back + Actions */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <Button
          variant="ghost"
          onClick={() => router.push("/dashboard/vpn")}
          className="gap-2 -ml-3"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Services
        </Button>
        <div className="flex gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowConfigDialog(true)}
          >
            <Download className="w-4 h-4 mr-1" />
            View Config
          </Button>
          {account.status === "active" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSuspendDialog(true)}
            >
              <PowerOff className="w-4 h-4 mr-1" />
              Suspend
            </Button>
          ) : account.status === "suspended" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                unsuspendMut.mutate({ accountId: account.id, reason: "manual" })
              }
              disabled={unsuspendMut.isPending}
            >
              {unsuspendMut.isPending ? (
                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
              ) : (
                <Power className="w-4 h-4 mr-1" />
              )}
              Reactivate
            </Button>
          ) : null}
        </div>
      </div>

      {/* Service Overview Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 mb-2">
            <Badge variant={statusVariant[account.status] || "outline"}>
              {statusLabel(account.status)}
            </Badge>
            <Badge variant="secondary" className="gap-1">
              {protocolIcons[account.protocol]}
              {protocolLabel(account.protocol)}
            </Badge>
          </div>
          <CardTitle className="text-2xl">
            {account.protocolLabel ? protocolLabel(account.protocol) : account.protocol}{" "}
            Service
          </CardTitle>
          <CardDescription>
            Service ID: {account.service_id}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Assigned IP</p>
            <p className="font-mono text-sm">{account.assigned_ip || "—"}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Connections</p>
            <p className="font-mono text-sm">
              {traffic?.usage.current_sessions ?? 0} / {account.max_connections || "—"}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Last Handshake</p>
            <p className="text-sm">
              {account.last_handshake_at
                ? new Date(account.last_handshake_at).toLocaleString()
                : "Never"}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Created</p>
            <p className="text-sm">
              {new Date(account.created_at).toLocaleDateString()}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Traffic & Bandwidth */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bandwidth Gauge */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Bandwidth Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Circular-ish progress */}
            <div className="relative w-40 h-40 mx-auto">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="hsl(var(--muted))"
                  strokeWidth="8"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke={
                    usagePct > 90
                      ? "hsl(var(--destructive))"
                      : usagePct > 75
                      ? "hsl(var(--warning, 38 92% 50%))"
                      : "hsl(var(--primary))"
                  }
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 40}`}
                  strokeDashoffset={`${2 * Math.PI * 40 * (1 - usagePct / 100)}`}
                  className="transition-all duration-1000"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold">
                  {usagePct.toFixed(1)}%
                </span>
                <span className="text-xs text-muted-foreground">used</span>
              </div>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Used</span>
                <span className="font-mono font-medium">
                  {traffic
                    ? formatTrafficBytes(traffic.usage.total_bytes)
                    : "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Upload</span>
                <span className="font-mono font-medium">
                  {traffic
                    ? formatTrafficBytes(traffic.usage.total_bytes_sent)
                    : "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Download</span>
                <span className="font-mono font-medium">
                  {traffic
                    ? formatTrafficBytes(traffic.usage.total_bytes_received)
                    : "—"}
                </span>
              </div>
              {traffic?.usage.bandwidth_limit_bytes && (
                <div className="flex justify-between pt-2 border-t">
                  <span className="text-muted-foreground">Limit</span>
                  <span className="font-mono font-medium">
                    {formatTrafficBytes(traffic.usage.bandwidth_limit_bytes)}
                  </span>
                </div>
              )}
              {traffic?.usage.bandwidth_remaining_bytes !== null &&
                traffic?.usage.bandwidth_remaining_bytes !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Remaining</span>
                    <span className="font-mono font-medium text-primary">
                      {formatTrafficBytes(traffic.usage.bandwidth_remaining_bytes)}
                    </span>
                  </div>
                )}
            </div>
          </CardContent>
        </Card>

        {/* Traffic Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Traffic History</CardTitle>
              <div className="flex gap-1">
                {timeRanges.map(({ key, label }) => (
                  <Button
                    key={key}
                    variant={timeRange === key ? "default" : "outline"}
                    size="sm"
                    className="h-7 text-xs px-2"
                    onClick={() => setTimeRange(key)}
                  >
                    {label}
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <BarChart3 className="w-12 h-12 mb-2 opacity-30" />
                <p>No traffic data available</p>
              </div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="sentGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="recvGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--chart-2, 210 50% 60%))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--chart-2, 210 50% 60%))" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 11 }}
                      stroke="hsl(var(--muted-foreground))"
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      stroke="hsl(var(--muted-foreground))"
                      tickFormatter={(v: number) => formatTrafficBytes(v)}
                    />
                    <Tooltip
                      formatter={(value: number) => formatTrafficBytes(value)}
                      labelStyle={{ color: "hsl(var(--foreground))" }}
                      contentStyle={{
                        background: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="sent"
                      name="Upload"
                      stroke="hsl(var(--primary))"
                      fill="url(#sentGradient)"
                      strokeWidth={2}
                    />
                    <Area
                      type="monotone"
                      dataKey="received"
                      name="Download"
                      stroke="hsl(var(--chart-2, 210 50% 60%))"
                      fill="url(#recvGradient)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sessions Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          {(!account.sessions || account.sessions.length === 0) ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Signal className="w-8 h-8 mb-2 opacity-30" />
              <p>No recent sessions</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium text-muted-foreground">Client IP</th>
                    <th className="pb-2 font-medium text-muted-foreground">Connected</th>
                    <th className="pb-2 font-medium text-muted-foreground">Disconnected</th>
                    <th className="pb-2 font-medium text-muted-foreground">Sent</th>
                    <th className="pb-2 font-medium text-muted-foreground">Received</th>
                  </tr>
                </thead>
                <tbody>
                  {account.sessions.slice(0, 10).map((sess) => (
                    <tr key={sess.id} className="border-b last:border-0">
                      <td className="py-2 font-mono">{sess.client_ip || "—"}</td>
                      <td className="py-2">
                        {sess.connected_at
                          ? new Date(sess.connected_at).toLocaleString()
                          : "—"}
                      </td>
                      <td className="py-2">
                        {sess.disconnected_at
                          ? new Date(sess.disconnected_at).toLocaleString()
                          : sess.status === "active"
                          ? "Active"
                          : "—"}
                      </td>
                      <td className="py-2 font-mono">
                        {formatTrafficBytes(sess.bytes_sent)}
                      </td>
                      <td className="py-2 font-mono">
                        {formatTrafficBytes(sess.bytes_received)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Config Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>VPN Configuration</DialogTitle>
            <DialogDescription>
              Use this configuration in your VPN client
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="relative">
              <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto max-h-64">
                {config?.config_text || "No configuration available"}
              </pre>
              {config?.config_text && (
                <Button
                  variant="outline"
                  size="icon"
                  className="absolute top-2 right-2 h-7 w-7"
                  onClick={handleCopyConfig}
                >
                  {copied ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </Button>
              )}
            </div>
            {config?.config_qr_base64 && (
              <div className="flex justify-center">
                <img
                  src={`data:image/png;base64,${config.config_qr_base64}`}
                  alt="VPN Config QR Code"
                  className="w-48 h-48"
                />
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Suspend Dialog */}
      <Dialog open={showSuspendDialog} onOpenChange={setShowSuspendDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-destructive" />
              Suspend VPN Service
            </DialogTitle>
            <DialogDescription>
              The VPN tunnel will be terminated and the service will be placed on hold.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="reason">Reason (optional)</Label>
              <input
                id="reason"
                className="w-full px-3 py-2 rounded-md border bg-background text-sm"
                placeholder="e.g., Maintenance, abuse, billing"
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowSuspendDialog(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                suspendMut.mutate({
                  accountId: account.id,
                  reason: suspendReason || "manual",
                });
                setShowSuspendDialog(false);
                setSuspendReason("");
              }}
              disabled={suspendMut.isPending}
            >
              {suspendMut.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  Suspending...
                </>
              ) : (
                "Confirm Suspend"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}