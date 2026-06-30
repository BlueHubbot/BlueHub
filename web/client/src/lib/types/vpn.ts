// VPN TypeScript types matching the API response schemas

// ─── Enums ────────────────────────────────────────────
export type VpnProtocol = "wireguard" | "xray" | "vless" | "trojan";
export type VpnAccountStatus =
  | "active"
  | "suspended"
  | "expired"
  | "terminated"
  | "provisioning"
  | "error";

// ─── VPN Account ──────────────────────────────────────
export interface VpnProtocolConfig {
  id: string;
  vpn_account_id: string;
  config_key: string;
  config_value: string;
  created_at: string;
  updated_at: string;
}

export interface VpnSession {
  id: string;
  vpn_account_id: string;
  status: string;
  connected_at: string | null;
  disconnected_at: string | null;
  client_ip: string | null;
  client_port: number | null;
  bytes_sent: number;
  bytes_received: number;
  server_endpoint: string | null;
  disconnect_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface VpnAccount {
  id: string;
  service_id: string;
  protocol: VpnProtocol;
  status: VpnAccountStatus;
  public_key: string | null;
  password: string | null;
  assigned_ip: string | null;
  dns_servers: string | null;
  allowed_ips: string | null;
  bandwidth_limit_bytes: number | null;
  bandwidth_used_bytes: number;
  max_connections: number | null;
  server_id: string | null;
  provisioned_at: string | null;
  last_handshake_at: string | null;
  client_config: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  protocol_configs: VpnProtocolConfig[];
  sessions: VpnSession[];
}

// ─── VPN Config ───────────────────────────────────────
export interface VpnConfigResponse {
  account_id: string;
  protocol: VpnProtocol;
  config_text: string | null;
  config_qr_base64: string | null;
}

// ─── VPN Traffic ──────────────────────────────────────
export interface VpnUsageSummary {
  total_bytes_sent: number;
  total_bytes_received: number;
  total_bytes: number;
  bandwidth_limit_bytes: number | null;
  bandwidth_remaining_bytes: number | null;
  bandwidth_used_percent: number | null;
  current_sessions: number;
  last_handshake_at: string | null;
}

export interface VpnTrafficResponse {
  account_id: string;
  protocol: VpnProtocol;
  status: VpnAccountStatus;
  usage: VpnUsageSummary;
}

// ─── VPN Service List ─────────────────────────────────
export interface VpnServiceListItem {
  service_id: string;
  account_id: string | null;
  protocol: VpnProtocol | null;
  status: string;
  assigned_ip: string | null;
  bandwidth_used_bytes: number;
  bandwidth_limit_bytes: number | null;
  expires_at: string | null;
  provisioned_at: string | null;
  last_handshake_at: string | null;
}

export interface VpnServiceListResponse {
  services: VpnServiceListItem[];
  total: number;
}

// ─── VPN Products ─────────────────────────────────────
export interface VpnProduct {
  id: string;
  name: string;
  description: string;
  protocols: VpnProtocol[];
  bandwidth: string | null;
  speed: string | null;
  price_monthly: number | null;
  price_quarterly: number | null;
  price_semi_annually: number | null;
  price_annually: number | null;
  is_active: boolean;
}

// ─── VPN Purchase ─────────────────────────────────────
export interface VpnPurchaseRequest {
  product_id: string;
  protocol: VpnProtocol;
  server_id?: string;
  billing_cycle: "monthly" | "quarterly" | "semi_annually" | "annually";
}

export interface VpnPurchaseResponse {
  payment_url: string;
  invoice_id: string;
  service_id: string;
  message: string;
}

// ─── VPN Server ───────────────────────────────────────
export interface VpnServer {
  id: string;
  name: string;
  host: string;
  port: number;
  public_ip: string | null;
  endpoint: string | null;
  country: string | null;
  city: string | null;
  provider: string | null;
  bandwidth_limit_mbps: number | null;
  max_clients: number;
  current_clients: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Requests ─────────────────────────────────────────
export interface VpnAccountCreate {
  service_id: string;
  protocol: VpnProtocol;
  server_id?: string;
  assigned_ip?: string;
  dns_servers?: string;
  allowed_ips?: string;
  bandwidth_limit_bytes?: number;
  max_connections?: number;
  notes?: string;
}

// ─── UI Helpers ───────────────────────────────────────
export function formatTrafficBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex++;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

export function statusLabel(status: VpnAccountStatus): string {
  const labels: Record<VpnAccountStatus, string> = {
    active: "Active",
    suspended: "Suspended",
    expired: "Expired",
    terminated: "Terminated",
    provisioning: "Provisioning",
    error: "Error",
  };
  return labels[status] || status;
}

export function protocolLabel(protocol: VpnProtocol): string {
  const labels: Record<VpnProtocol, string> = {
    wireguard: "WireGuard",
    xray: "VLESS+REALITY",
    vless: "VLESS",
    trojan: "Trojan",
  };
  return labels[protocol] || protocol;
}