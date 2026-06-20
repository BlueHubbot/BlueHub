"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Shield, Zap, Globe, Server, ArrowLeft, Check, Loader2 } from "lucide-react";
import { useVpnProducts, useVpnServers, usePurchaseVpn } from "@/lib/hooks/use-vpn";
import { protocolLabel, type VpnProtocol } from "@/lib/types/vpn";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";

const protocolIcons: Record<VpnProtocol, React.ReactNode> = {
  wireguard: <Zap className="w-4 h-4" />,
  xray: <Shield className="w-4 h-4" />,
  vless: <Globe className="w-4 h-4" />,
  trojan: <Server className="w-4 h-4" />,
};

type BillingCycle = "monthly" | "quarterly" | "semi_annually" | "annually";

const billingLabels: Record<BillingCycle, string> = {
  monthly: "Monthly",
  quarterly: "Quarterly",
  semi_annually: "Semi-Annual",
  annually: "Annual",
};

export default function VpnProductDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const productId = params.id;

  const { data: products, isLoading, error } = useVpnProducts();
  const { data: servers } = useVpnServers();
  const purchaseMutation = usePurchaseVpn();

  const [selectedProtocol, setSelectedProtocol] = useState<VpnProtocol | "">("");
  const [selectedServer, setSelectedServer] = useState<string>("");
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");

  const product = products?.find((p) => p.id === productId);

  // ─── Loading State ─────────────────────
  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-3xl space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-12 w-96" />
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  // ─── Error State ───────────────────────
  if (error) {
    const detail = (error as any)?.response?.data?.detail || (error as Error).message;
    return (
      <div className="container mx-auto py-8 px-4 max-w-3xl">
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{detail}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  // ─── Not Found ─────────────────────────
  if (!product) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-3xl">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-lg text-muted-foreground mb-4">Product not found.</p>
            <Button onClick={() => router.push("/dashboard/vpn/products")}>
              Back to Products
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const getPrice = (): number | null => {
    const priceMap: Record<BillingCycle, string> = {
      monthly: "price_monthly",
      quarterly: "price_quarterly",
      semi_annually: "price_semi_annually",
      annually: "price_annually",
    };
    const key = priceMap[billingCycle] as keyof typeof product;
    return (product[key] as number | null) || null;
  };

  const price = getPrice();
  const canPurchase =
    !!selectedProtocol && !!billingCycle && product.is_active && !purchaseMutation.isPending;

  const handlePurchase = () => {
    if (!canPurchase || !selectedProtocol) return;
    purchaseMutation.mutate({
      product_id: product.id,
      protocol: selectedProtocol,
      server_id: selectedServer || undefined,
      billing_cycle: billingCycle,
    });
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-3xl space-y-6">
      {/* Back Button */}
      <Button
        variant="ghost"
        onClick={() => router.push("/dashboard/vpn/products")}
        className="gap-2 -ml-3"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Products
      </Button>

      {/* Product Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 mb-2">
            {product.protocols.map((proto) => (
              <Badge key={proto} variant="secondary" className="gap-1">
                {protocolIcons[proto]}
                {protocolLabel(proto)}
              </Badge>
            ))}
            {!product.is_active && (
              <Badge variant="destructive">Unavailable</Badge>
            )}
          </div>
          <CardTitle className="text-2xl">{product.name}</CardTitle>
          <CardDescription className="text-base">{product.description}</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm">
          {product.bandwidth && (
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Bandwidth:</span>
              <span className="font-medium">{product.bandwidth}</span>
            </div>
          )}
          {product.speed && (
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Speed:</span>
              <span className="font-medium">{product.speed}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Purchase Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Configure & Purchase</CardTitle>
          <CardDescription>Select your preferences below</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Protocol Selection */}
          <div className="space-y-3">
            <Label>Protocol</Label>
            <RadioGroup
              value={selectedProtocol}
              onValueChange={(v) => setSelectedProtocol(v as VpnProtocol)}
            >
              <div className="grid grid-cols-2 gap-3">
                {product.protocols.map((proto) => (
                  <label
                    key={proto}
                    className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                      selectedProtocol === proto
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    <RadioGroupItem value={proto} id={`proto-${proto}`} />
                    <div className="flex items-center gap-2">
                      {protocolIcons[proto]}
                      <span className="font-medium">{protocolLabel(proto)}</span>
                    </div>
                  </label>
                ))}
              </div>
            </RadioGroup>
          </div>

          <Separator />

          {/* Server Selection */}
          {(servers || []).length > 0 && (
            <div className="space-y-3">
              <Label>Server Location</Label>
              <Select value={selectedServer} onValueChange={setSelectedServer}>
                <SelectTrigger>
                  <SelectValue placeholder="Auto-select (recommended)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Auto-select (recommended)</SelectItem>
                  {(servers || []).map((srv) => (
                    <SelectItem key={srv.id} value={srv.id}>
                      {srv.name} ({srv.country || srv.city || "Unknown"})
                      {srv.current_clients >= srv.max_clients && " — Full"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <Separator />

          {/* Billing Cycle */}
          <div className="space-y-3">
            <Label>Billing Cycle</Label>
            <RadioGroup
              value={billingCycle}
              onValueChange={(v) => setBillingCycle(v as BillingCycle)}
            >
              <div className="grid grid-cols-2 gap-3">
                {(
                  [
                    "monthly",
                    "quarterly",
                    "semi_annually",
                    "annually",
                  ] as BillingCycle[]
                ).map((cycle) => {
                  const cyclePriceMap: Record<
                    BillingCycle,
                    keyof typeof product
                  > = {
                    monthly: "price_monthly",
                    quarterly: "price_quarterly",
                    semi_annually: "price_semi_annually",
                    annually: "price_annually",
                  };
                  const cyclePrice = product[
                    cyclePriceMap[cycle]
                  ] as number | null;
                  if (!cyclePrice) return null;
                  return (
                    <label
                      key={cycle}
                      className={`flex items-center justify-between p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                        billingCycle === cycle
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <RadioGroupItem value={cycle} id={`cycle-${cycle}`} />
                        <Label
                          htmlFor={`cycle-${cycle}`}
                          className="cursor-pointer"
                        >
                          {billingLabels[cycle]}
                        </Label>
                      </div>
                      <span className="font-semibold">
                        ${(cyclePrice / 100).toFixed(2)}
                      </span>
                    </label>
                  );
                })}
              </div>
            </RadioGroup>
          </div>
        </CardContent>

        <Separator />

        {/* Price Summary & Purchase */}
        <CardFooter className="flex-col sm:flex-row sm:justify-between gap-4 pt-6">
          <div>
            <p className="text-sm text-muted-foreground">Total</p>
            <p className="text-3xl font-bold">
              {price !== null ? `$${(price / 100).toFixed(2)}` : "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              per {billingLabels[billingCycle].toLowerCase()} billing cycle
            </p>
          </div>
          <Button
            size="lg"
            className="w-full sm:w-auto min-w-[200px]"
            disabled={!canPurchase}
            onClick={handlePurchase}
          >
            {purchaseMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                Purchase Now
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}