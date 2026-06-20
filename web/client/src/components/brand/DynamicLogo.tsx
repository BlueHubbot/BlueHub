"use client";

import Image from "next/image";
import { getCachedTenantBranding, type TenantBranding } from "@/lib/hooks/use-tenant";
import { useEffect, useState } from "react";
import { Shield } from "lucide-react";
import { useTenantBranding } from "@/lib/hooks/use-tenant";

interface DynamicLogoProps {
  className?: string;
  iconSize?: number;
  showText?: boolean;
}

function LogoIcon({ className, iconSize = 32 }: { className?: string; iconSize?: number }) {
  return <Shield className={className} size={iconSize} />;
}

function LogoText({ branding }: { branding: TenantBranding | null }) {
  const companyName = branding?.company_name || getCachedTenantBranding().company_name || "BlueHub";
  return (
    <span className="font-bold text-xl ml-2">
      {companyName}
    </span>
  );
}

export function DynamicLogo({ className = "", iconSize = 32, showText = true }: DynamicLogoProps) {
  const { data: branding } = useTenantBranding();
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const cached = getCachedTenantBranding();
    if (cached.logo_url) {
      setLogoUrl(cached.logo_url);
    }
    setMounted(true);
  }, []);

  useEffect(() => {
    if (branding?.logo_url) {
      setLogoUrl(branding.logo_url);
    }
  }, [branding]);

  if (!mounted) {
    return (
      <div className={`flex items-center ${className}`}>
        <LogoIcon iconSize={iconSize} className="text-primary" />
        {showText && <span className="font-bold text-xl ml-2">BlueHub</span>}
      </div>
    );
  }

  if (logoUrl) {
    return (
      <div className={`flex items-center ${className}`}>
        <Image
          src={logoUrl}
          alt={branding?.company_name || "Logo"}
          width={iconSize * 4}
          height={iconSize}
          className="h-8 w-auto object-contain"
          priority
        />
      </div>
    );
  }

  return (
    <div className={`flex items-center ${className}`}>
      <LogoIcon iconSize={iconSize} className="text-primary" />
      {showText && <LogoText branding={branding || null} />}
    </div>
  );
}

export function DynamicFavicon() {
  const { data: branding } = useTenantBranding();
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);

  useEffect(() => {
    const cached = getCachedTenantBranding();
    if (cached.favicon_url) {
      setFaviconUrl(cached.favicon_url);
    }
  }, []);

  useEffect(() => {
    if (branding?.favicon_url) {
      setFaviconUrl(branding.favicon_url);
    }
  }, [branding]);

  useEffect(() => {
    if (faviconUrl && typeof window !== "undefined") {
      const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
      if (link) {
        link.href = faviconUrl;
      }
    }
  }, [faviconUrl]);

  return null;
}