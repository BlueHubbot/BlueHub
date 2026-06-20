"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Wifi,
  Shield,
  Zap,
  Globe,
  Server,
  Clock,
  MoreHorizontal,
  ArrowUpDown,
  Search,
  Download,
  QrCode,
} from "lucide-react";
import { useVpnServices } from "@/lib/hooks/use-vpn";
import { formatTrafficBytes, statusLabel, protocolLabel, type VpnProtocol } from "@/lib/types/vpn";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const protocolIcons: Record<string, React.ReactNode> = {
  wireguard: <Zap className="w-4 h-4" />,
  xray: <Shield className="w-4 h-4" />,
  vless: <Globe className="w-4 h-4" />,
  trojan: <Server className="w-4 h-4" />,
};

const statusVariants: Record<string, string> = {
  active: "default",
  suspended: "secondary",
  expired: "destructive",
  terminated: "destructive",
  provisioning: "outline",
  error: "destructive",
};

export default function VpnServicesPage() {
  const router = useRouter();
  const { data: servicesResponse, isLoading, error } = useVpnServices();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [protocolFilter, setProtocolFilter] = useState<string>("all");

  // Modal state for config/QR
  const [configModal, setConfigModal] = useState<{
    open: boolean;
    configText: string | null;
    qrBase64: string | null;
    name: string;
  }>({ open: false, configText: null, qrBase64: null, name: "" });

  // ─── Extract unique protocols from services ──────
  const services = servicesResponse?.services || [];
  const allProtocols = Array.from(
    new Set(services.map((s) => s.protocol).filter(Boolean))
  ) as string[];

  // ─── Filtering ─────────────────────────────────────
  const filteredServices = services.filter((svc) => {
    if (statusFilter !== "all" && svc.status !== statusFilter) return false;
    if (protocolFilter !== "all" && svc.protocol !== protocolFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        svc.service_id?.toLowerCase().includes(q) ||
        svc.assigned_ip?.toLowerCase().includes(q) ||
        svc.protocol?.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  // ─── Loading State ─────────────────────────────────
  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 space-y-6">
        <div>
          <Skeleton className="h-9 w-48 mb-2" />
          <Skeleton className="h-5 w-72" />
        </div>
        <div className="flex gap-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-40" />
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  // ─── Error State ───────────────────────────────────
  if (error) {
    const detail = (error as any)?.response?.data?.detail || (error as Error).message;
    return (
      <div className="container mx-auto py-8 px-4">
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Error loading VPN services</CardTitle>
            <CardDescription>{detail}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My VPN Services</h1>
          <p className="text-muted-foreground mt-1">
            Manage your active VPN subscriptions
          </p>
        </div>
        <Button onClick={() => router.push("/dashboard/vpn/products")}>
          <Download className="w-4 h-4 mr-2" />
          Purchase New
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search by ID, IP, or protocol..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="suspended">Suspended</SelectItem>
            <SelectItem value="expired">Expired</SelectItem>
            <SelectItem value="provisioning">Provisioning</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
        <Select value={protocolFilter} onValueChange={setProtocolFilter}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Protocols" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Protocols</SelectItem>
            {allProtocols.map((proto) => (
              <SelectItem key={proto} value={proto}>
                {protocolLabel(proto)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Service List */}
      {filteredServices.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center space-y-4">
            <Wifi className="w-12 h-12 mx-auto text-muted-foreground/30" />
            <div>
              <p className="text-lg font-medium text-muted-foreground">
                {services.length === 0
                  ? "No VPN services yet"
                  : "No services match your filters"}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {services.length === 0
                  ? "Purchase a VPN plan to get started"
                  : "Try adjusting your search or filters"}
              </p>
            </div>
            {services.length === 0 && (
              <Button onClick={() => router.push("/dashboard/vpn/products")}>
                Browse Products
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredServices.map((svc) => {
            const usagePct =
              svc.bandwidth_limit_bytes && svc.bandwidth_limit_bytes > 0
                ? Math.min(
                    100,
                    ((svc.bandwidth_used_bytes || 0) / svc.bandwidth_limit_bytes) * 100
                  )
                : null;
            return (
              <Card
                key={svc.service_id + (svc.account_id || "")}
                className="group hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => {
                  if (svc.account_id) {
                    router.push(`/dashboard/vpn/services/${svc.account_id}`);
                  }
                }}
              >
                <CardContent className="p-4 sm:p-6">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                    {/* Icon + Info */}
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <div className="hidden sm:flex h-12 w-12 rounded-full bg-primary/10 items-center justify-center shrink-0">
                        {svc.protocol && protocolIcons[svc.protocol] ? (
                          <span className="text-primary">{protocolIcons[svc.protocol]}</span>
                        ) : (
                          <Wifi className="w-5 h-5 text-primary" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold truncate">
                            {svc.protocol ? protocolLabel(svc.protocol) : "VPN"} Service
                          </span>
                          <Badge variant={(statusVariants[svc.status] || "outline") as any}>
                            {statusLabel(svc.status)}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1 flex-wrap">
                          <span className="font-mono text-xs">
                            ID: {svc.service_id?.slice(0, 12)}...
                          </span>
                          {svc.assigned_ip && (
                            <span className="font-mono text-xs">{svc.assigned_ip}</span>
                          )}
                          {svc.expires_at && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              Expires {new Date(svc.expires_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Usage Bar */}
                    <div className="w-full sm:w-48 shrink-0">
                      {usagePct !== null ? (
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">
                              {formatTrafficBytes(svc.bandwidth_used_bytes || 0)}
                            </span>
                            <span className="text-muted-foreground">
                              {formatTrafficBytes(svc.bandwidth_limit_bytes || 0)}
                            </span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                usagePct > 90
                                  ? "bg-destructive"
                                  : usagePct > 75
                                  ? "bg-yellow-500"
                                  : "bg-primary"
                              }`}
                              style={{ width: `${Math.min(100, usagePct)}%` }}
                            />
                          </div>
                          <p className="text-xs text-right text-muted-foreground">
                            {usagePct.toFixed(1)}% used
                          </p>
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground text-center">
                          Unlimited bandwidth
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (svc.account_id) {
                            router.push(`/dashboard/vpn/services/${svc.account_id}`);
                          }
                        }}
                      >
                        <ArrowUpDown className="w-3.5 h-3.5 mr-1" />
                        Details
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Summary Info */}
      <Card className="bg-muted/50">
        <CardContent className="py-4 px-6">
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-muted-foreground">Total Services:</span>{" "}
              <span className="font-semibold">{services.length}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Active:</span>{" "}
              <span className="font-semibold text-green-600">
                {services.filter((s) => s.status === "active").length}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Suspended:</span>{" "}
              <span className="font-semibold text-yellow-600">
                {services.filter((s) => s.status === "suspended").length}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Expired:</span>{" "}
              <span className="font-semibold text-red-600">
                {services.filter((s) => s.status === "expired").length}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}