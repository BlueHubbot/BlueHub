import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";

export interface TenantBranding {
  logo_url?: string;
  favicon_url?: string;
  primary_color?: string;
  secondary_color?: string;
  accent_color?: string;
  page_title?: string;
  company_name?: string;
}

const DEFAULT_BRANDING: TenantBranding = {
  logo_url: undefined,
  favicon_url: undefined,
  primary_color: "221.2 83.2% 53.3%",
  secondary_color: "210 40% 96.1%",
  accent_color: "210 40% 96.1%",
  page_title: "BlueHub",
  company_name: "BlueHub",
};

async function fetchTenantBranding(): Promise<TenantBranding> {
  const response = await apiClient.client.get("/tenants/current");
  const tenant = response.data;

  const branding: TenantBranding = {
    logo_url: tenant.logo_url || undefined,
    favicon_url: tenant.favicon_url || undefined,
    primary_color: tenant.primary_color || DEFAULT_BRANDING.primary_color,
    secondary_color: tenant.secondary_color || DEFAULT_BRANDING.secondary_color,
    accent_color: tenant.accent_color || DEFAULT_BRANDING.accent_color,
    page_title: tenant.page_title || tenant.company_name || DEFAULT_BRANDING.page_title,
    company_name: tenant.company_name || DEFAULT_BRANDING.company_name,
  };

  return branding;
}

export function useTenantBranding() {
  return useQuery<TenantBranding>({
    queryKey: ["tenant-branding"],
    queryFn: async () => {
      try {
        const branding = await fetchTenantBranding();
        // Cache to localStorage
        if (typeof window !== "undefined") {
          localStorage.setItem("tenant_branding", JSON.stringify(branding));
        }
        return branding;
      } catch (error) {
        // Fallback to cached or default
        if (typeof window !== "undefined") {
          const cached = localStorage.getItem("tenant_branding");
          if (cached) {
            return JSON.parse(cached) as TenantBranding;
          }
        }
        return DEFAULT_BRANDING;
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function getCachedTenantBranding(): TenantBranding {
  if (typeof window === "undefined") return DEFAULT_BRANDING;
  try {
    const cached = localStorage.getItem("tenant_branding");
    if (cached) {
      return JSON.parse(cached) as TenantBranding;
    }
  } catch {
    // ignore
  }
  return DEFAULT_BRANDING;
}

export { DEFAULT_BRANDING };