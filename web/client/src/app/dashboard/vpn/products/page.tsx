"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Zap, Globe, Server } from "lucide-react";
import { useVpnProducts, useVpnServers } from "@/lib/hooks/use-vpn";
import { protocolLabel, type VpnProtocol } from "@/lib/types/vpn";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const protocolIcons: Record<VpnProtocol, React.ReactNode> = {
  wireguard: <Zap className="w-4 h-4" />,
  xray: <Shield className="w-4 h-4" />,
  vless: <Globe className="w-4 h-4" />,
  trojan: <Server className="w-4 h-4" />,
};

export default function VpnProductsPage() {
  const router = useRouter();
  const { data: products, isLoading, error } = useVpnProducts();
  const { data: servers, isLoading: serversLoading } = useVpnServers();
  const [selectedServer, setSelectedServer] = useState<string>("");
  const [selectedProtocol, setSelectedProtocol] = useState<string>("all");

  // ─── Loading State ─────────────────────
  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 space-y-8">
        <div>
          <Skeleton className="h-9 w-64 mb-2" />
          <Skeleton className="h-5 w-96" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-80 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  // ─── Error State ───────────────────────
  if (error) {
    const detail = (error as any)?.response?.data?.detail || (error as Error).message;
    return (
      <div className="container mx-auto py-8 px-4">
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Error loading products</CardTitle>
            <CardDescription>{detail}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  // ─── Filter products ───────────────────
  const filteredProducts = (products || []).filter((p) => {
    if (selectedProtocol !== "all" && !p.protocols.includes(selectedProtocol as VpnProtocol)) {
      return false;
    }
    return true;
  });

  // ─── Collect unique protocols ──────────
  const allProtocols = Array.from(
    new Set((products || []).flatMap((p) => p.protocols))
  );

  return (
    <div className="container mx-auto py-8 px-4 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">VPN Products</h1>
          <p className="text-muted-foreground mt-1">
            Choose a VPN plan that fits your needs
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="w-full sm:w-48">
          <Select value={selectedProtocol} onValueChange={setSelectedProtocol}>
            <SelectTrigger>
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

        {!serversLoading && (servers || []).length > 0 && (
          <div className="w-full sm:w-48">
            <Select value={selectedServer} onValueChange={setSelectedServer}>
              <SelectTrigger>
                <SelectValue placeholder="All Servers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Servers</SelectItem>
                {(servers || []).map((srv) => (
                  <SelectItem key={srv.id} value={srv.id}>
                    {srv.name} ({srv.country || srv.city || "Unknown"})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {/* Product Grid */}
      {filteredProducts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground text-lg">No products found matching your filters.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProducts.map((product) => (
            <Card
              key={product.id}
              className="group hover:shadow-lg transition-all duration-200 hover:-translate-y-1 cursor-pointer border-2 hover:border-primary/50"
              onClick={() => router.push(`/dashboard/vpn/products/${product.id}`)}
            >
              <CardHeader>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {product.protocols.map((proto) => (
                      <Badge key={proto} variant="secondary" className="gap-1">
                        {protocolIcons[proto]}
                        {protocolLabel(proto)}
                      </Badge>
                    ))}
                  </div>
                  {!product.is_active && (
                    <Badge variant="destructive">Unavailable</Badge>
                  )}
                </div>
                <CardTitle className="group-hover:text-primary transition-colors">
                  {product.name}
                </CardTitle>
                <CardDescription>{product.description}</CardDescription>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Specs */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {product.bandwidth && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Globe className="w-4 h-4" />
                      <span>{product.bandwidth}</span>
                    </div>
                  )}
                  {product.speed && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Zap className="w-4 h-4" />
                      <span>{product.speed}</span>
                    </div>
                  )}
                </div>

                {/* Pricing */}
                <div className="pt-4 border-t space-y-2">
                  {product.price_monthly && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Monthly</span>
                      <span className="font-semibold">
                        ${(product.price_monthly / 100).toFixed(2)}
                      </span>
                    </div>
                  )}
                  {product.price_quarterly && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Quarterly</span>
                      <span className="font-semibold">
                        ${(product.price_quarterly / 100).toFixed(2)}
                      </span>
                    </div>
                  )}
                  {product.price_semi_annually && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Semi-Annual</span>
                      <span className="font-semibold">
                        ${(product.price_semi_annually / 100).toFixed(2)}
                      </span>
                    </div>
                  )}
                  {product.price_annually && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Annually</span>
                      <span className="font-semibold">
                        ${(product.price_annually / 100).toFixed(2)}
                      </span>
                    </div>
                  )}
                </div>

                <Button
                  className="w-full mt-2"
                  disabled={!product.is_active}
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/dashboard/vpn/products/${product.id}`);
                  }}
                >
                  View & Purchase
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}