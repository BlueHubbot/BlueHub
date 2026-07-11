import axios, { AxiosInstance } from "axios";

// آدرس مستقیم بک‌آند پایتون بدون پیشوند مجازی
const API_BASE_URL = "http://109.199.108.30:8000";

const _api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  const localToken = localStorage.getItem("admin_token");
  if (localToken) return localToken;

  const match = document.cookie.match(new RegExp('(^| )admin_token=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

_api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // اگر آدرس لاگین است، دقیقاً به /auth/login فرستاده شود (بدون api/v1)
  if (config.url === "/api/v1/auth/login" || config.url === "auth/login") {
    config.url = "/auth/login";
  }
  return config;
});

_api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("admin_token");
        document.cookie = "admin_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;";
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export const api = _api as unknown as Omit<AxiosInstance, "get" | "post" | "put" | "patch" | "delete"> & {
  get<T = any>(url: string, config?: Record<string, unknown>): Promise<T>;
  post<T = any>(url: string, data?: unknown, config?: Record<string, unknown>): Promise<T>;
  put<T = any>(url: string, data?: unknown, config?: Record<string, unknown>): Promise<T>;
  patch<T = any>(url: string, data?: unknown, config?: Record<string, unknown>): Promise<T>;
  delete<T = any>(url: string, config?: Record<string, unknown>): Promise<T>;
};

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

// تمام آدرس‌ها دقیقاً بر اساس Prefixهای تعریف شده در پایتون بدون اسلش اول
export const adminApi = {
  getDashboardStats: () => api.get<DashboardStats>("admin/dashboard/stats"),
  
  // بخش ماژول‌ها در پایتون پریفیکس /admin ندارد و مستقیم روی /modules تعریف شده است
  getModules: () => api.get<ModuleRegistryEntry[]>("modules"),
  updateModule: (name: string, data: ModuleTogglePayload) => api.patch<ModuleRegistryEntry>(`modules/${name}`, data),
  getModuleServicesCount: (name: string) => api.get<{ count: number }>(`modules/${name}/services`),
  
  createProduct: (data: Record<string, unknown>) => api.post("admin/products", data),
  updateProduct: (id: number, data: Record<string, unknown>) => api.put(`admin/products/${id}`, data),
  deleteProduct: (id: number) => api.delete(`admin/products/${id}`),
  getTenants: () => api.get("admin/tenants"),
  createTenant: (data: Record<string, unknown>) => api.post("admin/tenants", data),
  updateTenant: (id: number, data: Record<string, unknown>) => api.put(`admin/tenants/${id}`, data),
  getUsers: (params?: { tenant_id?: number; role?: string }) => api.get("admin/users", { params }),
  updateUser: (id: number, data: Record<string, unknown>) => api.patch(`admin/users/${id}`, data),
  suspendService: (id: number) => api.post(`admin/services/${id}/suspend`),
  getAbuseReports: () => api.get("admin/abuse-reports"),
};