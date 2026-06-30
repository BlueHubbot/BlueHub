"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/lib/api-client";
import type {
  VpnAccount,
  VpnConfigResponse,
  VpnTrafficResponse,
  VpnServiceListResponse,
  VpnProduct,
  VpnPurchaseRequest,
  VpnPurchaseResponse,
  VpnServer,
} from "@/lib/types/vpn";

// ──────────────────────────────────────────────
// Query Key Factory
// ──────────────────────────────────────────────
export const vpnKeys = {
  all: ["vpn"] as const,
  accounts: () => [...vpnKeys.all, "accounts"] as const,
  account: (id: string) => [...vpnKeys.accounts(), id] as const,
  accountConfig: (id: string) => [...vpnKeys.account(id), "config"] as const,
  accountTraffic: (id: string) => [...vpnKeys.account(id), "traffic"] as const,
  services: () => [...vpnKeys.all, "services"] as const,
  products: () => [...vpnKeys.all, "products"] as const,
  product: (id: string) => [...vpnKeys.products(), id] as const,
  servers: () => [...vpnKeys.all, "servers"] as const,
  server: (id: string) => [...vpnKeys.servers(), id] as const,
};

// ──────────────────────────────────────────────
// Hook: List VPN Accounts
// ──────────────────────────────────────────────
export function useVpnAccounts(filters?: {
  service_id?: string;
  protocol?: string;
  status?: string;
  server_id?: string;
}) {
  return useQuery({
    queryKey: [...vpnKeys.accounts(), filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.service_id) params.set("service_id", filters.service_id);
      if (filters?.protocol) params.set("protocol", filters.protocol);
      if (filters?.status) params.set("status", filters.status);
      if (filters?.server_id) params.set("server_id", filters.server_id);
      const query = params.toString();
      const { data } = await apiClient.client.get<VpnAccount[]>(
        `/vpn/accounts${query ? `?${query}` : ""}`
      );
      return data;
    },
    staleTime: 30_000, // 30s — accounts change infrequently
  });
}

// ──────────────────────────────────────────────
// Hook: Single VPN Account
// ──────────────────────────────────────────────
export function useVpnAccount(accountId: string | undefined) {
  return useQuery({
    queryKey: vpnKeys.account(accountId || ""),
    queryFn: async () => {
      const { data } = await apiClient.client.get<VpnAccount>(
        `/vpn/accounts/${accountId}`
      );
      return data;
    },
    enabled: !!accountId,
    staleTime: 30_000,
  });
}

// ──────────────────────────────────────────────
// Hook: VPN Config (with optional QR)
// ──────────────────────────────────────────────
export function useVpnConfig(accountId: string | undefined, includeQr = true) {
  return useQuery({
    queryKey: [...vpnKeys.accountConfig(accountId || ""), includeQr],
    queryFn: async () => {
      const { data } = await apiClient.client.get<VpnConfigResponse>(
        `/vpn/accounts/${accountId}/config?include_qr=${includeQr}`
      );
      return data;
    },
    enabled: !!accountId,
    staleTime: 5 * 60_000, // 5 min — config changes rarely
  });
}

// ──────────────────────────────────────────────
// Hook: VPN Traffic (polling every 60s)
// ──────────────────────────────────────────────
export function useVpnTraffic(accountId: string | undefined) {
  return useQuery({
    queryKey: vpnKeys.accountTraffic(accountId || ""),
    queryFn: async () => {
      const { data } = await apiClient.client.get<VpnTrafficResponse>(
        `/vpn/accounts/${accountId}/traffic`
      );
      return data;
    },
    enabled: !!accountId,
    refetchInterval: 60_000, // Auto-poll every 60 seconds
    staleTime: 30_000,
  });
}

// ──────────────────────────────────────────────
// Hook: List VPN Services
// ──────────────────────────────────────────────
export function useVpnServices() {
  return useQuery({
    queryKey: vpnKeys.services(),
    queryFn: async () => {
      const { data } = await apiClient.client.get<VpnServiceListResponse>(
        "/vpn/services"
      );
      return data;
    },
    staleTime: 30_000,
  });
}

// ──────────────────────────────────────────────
// Hook: VPN Products
// ──────────────────────────────────────────────
export function useVpnProducts() {
  return useQuery({
    queryKey: vpnKeys.products(),
    queryFn: async () => {
      const { data } = await apiClient.client.get<VpnProduct[]>("/vpn/products");
      return data;
    },
    staleTime: 5 * 60_000, // Products change rarely
  });
}

// ──────────────────────────────────────────────
// Hook: Create VPN Account
// ──────────────────────────────────────────────
export function useCreateVpnAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body: {
      service_id: string;
      protocol: string;
      server_id?: string;
      assigned_ip?: string;
      dns_servers?: string;
      allowed_ips?: string;
      bandwidth_limit_bytes?: number;
      max_connections?: number;
      notes?: string;
    }) => {
      const { data } = await apiClient.client.post<VpnAccount>(
        "/vpn/accounts",
        body
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: vpnKeys.accounts() });
      toast.success("VPN account created successfully");
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || error.message || "Failed to create VPN account";
      toast.error(detail);
    },
  });
}

// ──────────────────────────────────────────────
// Hook: Update VPN Account
// ──────────────────────────────────────────────
export function useUpdateVpnAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      accountId,
      ...body
    }: {
      accountId: string;
      protocol?: string;
      status?: string;
      assigned_ip?: string;
      dns_servers?: string;
      allowed_ips?: string;
      bandwidth_limit_bytes?: number;
      max_connections?: number;
      notes?: string;
    }) => {
      const { data } = await apiClient.client.patch<VpnAccount>(
        `/vpn/accounts/${accountId}`,
        body
      );
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: vpnKeys.accounts() });
      queryClient.invalidateQueries({
        queryKey: vpnKeys.account(variables.accountId),
      });
      toast.success("VPN account updated");
    },
    onError: (error: any) => {
      toast.error(
        error?.response?.data?.detail || error.message || "Update failed"
      );
    },
  });
}

// ──────────────────────────────────────────────
// Hook: Delete VPN Account
// ──────────────────────────────────────────────
export function useDeleteVpnAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (accountId: string) => {
      await apiClient.client.delete(`/vpn/accounts/${accountId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: vpnKeys.accounts() });
      toast.success("VPN account deleted");
    },
    onError: (error: any) => {
      toast.error(
        error?.response?.data?.detail || error.message || "Delete failed"
      );
    },
  });
}

// ──────────────────────────────────────────────
// Hook: Suspend / Unsuspend VPN Account
// ──────────────────────────────────────────────
export function useSuspendVpnAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      accountId,
      reason,
    }: {
      accountId: string;
      reason?: string;
    }) => {
      const { data } = await apiClient.client.post<VpnAccount>(
        `/vpn/accounts/${accountId}/suspend?reason=${reason || "manual"}`
      );
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: vpnKeys.accounts() });
      queryClient.invalidateQueries({
        queryKey: vpnKeys.account(variables.accountId),
      });
      toast.success("VPN account suspended");
    },
    onError: (error: any) => {
      toast.error(
        error?.response?.data?.detail || error.message || "Suspend failed"
      );
    },
  });
}

export function useUnsuspendVpnAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      accountId,
      reason,
    }: {
      accountId: string;
      reason?: string;
    }) => {
      const { data } = await apiClient.client.post<VpnAccount>(
        `/vpn/accounts/${accountId}/unsuspend?reason=${reason || "manual"}`
      );
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: vpnKeys.accounts() });
      queryClient.invalidateQueries({
        queryKey: vpnKeys.account(variables.accountId),
      });
      toast.success("VPN account reactivated");
    },
    onError: (error: any) => {
      toast.error(
        error?.response?.data?.detail || error.message || "Unsuspend failed"
      );
    },
  });
}

// ──────────────────────────────────────────────
// Hook: Purchase VPN
// ──────────────────────────────────────────────
export function usePurchaseVpn() {
  return useMutation({
    mutationFn: async (body: VpnPurchaseRequest) => {
      const { data } = await apiClient.client.post<VpnPurchaseResponse>(
        "/vpn/purchase",
        body
      );
      return data;
    },
    onSuccess: (response: VpnPurchaseResponse) => {
      if (response.payment_url) {
        window.open(response.payment_url, "_blank");
      }
      toast.success(response.message || "Purchase initiated");
    },
    onError: (error: any) => {
      toast.error(
        error?.response?.data?.detail || error.message || "Purchase failed"
      );
    },
  });
}

// ──────────────────────────────────────────────
// Hook: VPN Servers
// ──────────────────────────────────────────────
export function useVpnServers(includeInactive = false) {
  return useQuery({
    queryKey: [...vpnKeys.servers(), includeInactive],
    queryFn: async () => {
      const { data } = await apiClient.client.get<VpnServer[]>(
        `/vpn/servers?include_inactive=${includeInactive}`
      );
      return data;
    },
    staleTime: 2 * 60_000,
  });
}