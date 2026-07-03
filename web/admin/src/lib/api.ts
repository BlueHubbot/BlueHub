import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to attach auth token
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("admin_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("admin_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Type Definitions ──────────────────────────────────────────────────────

export interface ModuleFlag {
  enabled: boolean;
  stop_new_sales: boolean;
  terminate_services: boolean;
  maintenance_mode: boolean;
}

export interface ModuleRegistryEntry {
  id?: string | null;
  module_name: string;
  display_name: string;
  description?: string | null;
  version: string;
  enabled: boolean;
  order: number;
  flags: ModuleFlag;
  config_schema?: Record<string, unknown> | null;
  default_config?: Record<string, unknown> | null;
}

export interface ModuleTogglePayload {
  enabled?: boolean;
  stop_new_sales?: boolean;
  terminate_services?: boolean;
  maintenance_mode?: boolean;
}

export interface DashboardStats {
  total_users: number;
  active_services: number;
  revenue_monthly: number;
  active_modules: number;
  total_tenants: number;
  pending_abuse_reports: number;
}

// ── Admin API Endpoints ───────────────────────────────────────────────────

export const adminApi = {
  // Dashboard stats
  getDashboardStats: () =>
    api.get<DashboardStats>("/admin/dashboard/stats"),

  // Modules
  getModules: () =>
    api.get<ModuleRegistryEntry[]>("/admin/modules"),
  updateModule: (name: string, data: ModuleTogglePayload) =>
    api.patch<ModuleRegistryEntry>(`/admin/modules/${name}`, data),
  getModuleServicesCount: (name: string) =>
    api.get<{ count: number }>(`/admin/modules/${name}/services`),

  // Products
  createProduct: (data: Record<string, unknown>) =>
    api.post("/admin/products", data),
  updateProduct: (id: number, data: Record<string, unknown>) =>
    api.put(`/admin/products/${id}`, data),
  deleteProduct: (id: number) =>
    api.delete(`/admin/products/${id}`),

  // Tenants
  getTenants: () => api.get("/admin/tenants"),
  createTenant: (data: Record<string, unknown>) =>
    api.post("/admin/tenants", data),
  updateTenant: (id: number, data: Record<string, unknown>) =>
    api.put(`/admin/tenants/${id}`, data),

  // Users
  getUsers: (params?: { tenant_id?: number; role?: string }) =>
    api.get("/admin/users", { params }),
  updateUser: (id: number, data: Record<string, unknown>) =>
    api.patch(`/admin/users/${id}`, data),

  // Services
  suspendService: (id: number) =>
    api.post(`/admin/services/${id}/suspend`),

  // Abuse Reports
  getAbuseReports: () => api.get("/admin/abuse-reports"),
};