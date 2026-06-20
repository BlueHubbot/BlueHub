"use client";

import { useEffect, useState } from "react";
import { useTenantBranding, getCachedTenantBranding, type TenantBranding } from "@/lib/hooks/use-tenant";
import { usePathname } from "next/navigation";

interface TenantThemeProviderProps {
  children: React.ReactNode;
}

function applyBranding(branding: TenantBranding) {
  if (typeof window === "undefined") return;
  const root = document.documentElement;

  if (branding.primary_color) {
    root.style.setProperty("--primary", branding.primary_color);
  }
  if (branding.secondary_color) {
    root.style.setProperty("--secondary", branding.secondary_color);
  }
  if (branding.accent_color) {
    root.style.setProperty("--accent", branding.accent_color);
  }
  if (branding.company_name) {
    root.style.setProperty("--company-name", JSON.stringify(branding.company_name));
  }

  // Update page title
  if (branding.page_title) {
    document.title = branding.page_title;
  }

  // Update favicon
  if (branding.favicon_url) {
    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (link) {
      link.href = branding.favicon_url;
    } else {
      const newLink = document.createElement("link");
      newLink.rel = "icon";
      newLink.href = branding.favicon_url;
      document.head.appendChild(newLink);
    }
  }

  // Update theme color meta tag
  if (branding.primary_color) {
    let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "theme-color";
      document.head.appendChild(meta);
    }
    // Convert HSL to hex approximation for meta tag
    meta.content = `hsl(${branding.primary_color})`;
  }
}

export function TenantThemeProvider({ children }: TenantThemeProviderProps) {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  // Apply cached branding immediately on mount
  useEffect(() => {
    const cached = getCachedTenantBranding();
    applyBranding(cached);
    setMounted(true);
  }, []);

  // Fetch live branding and apply
  const { data: branding } = useTenantBranding();

  useEffect(() => {
    if (branding) {
      applyBranding(branding);
    }
  }, [branding]);

  // Re-apply branding on route change (for page title)
  useEffect(() => {
    if (branding && branding.page_title) {
      document.title = branding.page_title;
    }
  }, [pathname, branding]);

  if (!mounted) {
    return <>{children}</>;
  }

  return <>{children}</>;
}