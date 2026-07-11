"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getUser } from "@/lib/auth";
import {
  Plus,
  Search,
  Building2,
  Copy,
  Check,
  ExternalLink,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { TenantFormModal } from "./components/TenantFormModal";

export interface TenantData {
  id: string;
  name: string;
  domain: string;
  logo_url: string | null;
  branding_config: Record<string, unknown> | null;
  telegram_bot_token: string | null;
  license_key: string;
  signature: string | null;
  active: boolean;
  created_at?: string;
  updated_at?: string;
}

export default function TenantsPage() {
  const router = useRouter();
  const user = getUser();
  const [tenants, setTenants] = useState<TenantData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingTenant, setEditingTenant] = useState<TenantData | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const fetchTenants = useCallback(async () => {
    try {
      setError(null);
      const res = await api.get<TenantData[]>("/admin/tenants");
      setTenants(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load tenants";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || user.role !== "superadmin") {
      router.push("/login");
      return;
    }
    fetchTenants();
  }, [user, router, fetchTenants]);

  const filtered = tenants.filter((t) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      t.name.toLowerCase().includes(q) ||
      t.domain.toLowerCase().includes(q) ||
      t.license_key.toLowerCase().includes(q)
    );
  });

  const handleToggleActive = async (tenant: TenantData) => {
    try {
      setError(null);
      await api.patch(`/admin/tenants/${tenant.id}`, { active: !tenant.active });
      await fetchTenants();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to toggle tenant status";
      setError(msg);
    }
  };

  const handleSaved = () => {
    setFormOpen(false);
    setEditingTenant(null);
    fetchTenants();
  };

  const handleCopyKey = async (key: string) => {
    try {
      await navigator.clipboard.writeText(key);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = key;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  // Extract branding colors for preview
  const getBrandColor = (tenant: TenantData): string => {
    if (tenant.branding_config && typeof tenant.branding_config === "object") {
      const cfg = tenant.branding_config as Record<string, string>;
      return cfg.primaryColor || cfg.primary_color || "#3b82f6";
    }
    return "#3b82f6";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tenants</h1>
          <p className="text-sm text-muted-foreground">
            Manage white-label organizations with isolated branding, domains, and license keys.
          </p>
        </div>
        <button
          onClick={() => {
            setEditingTenant(null);
            setFormOpen(true);
          }}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Tenant
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          <p>{error}</p>
          <button onClick={() => setError(null)} className="mt-1 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by name, domain, or license key..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border bg-background py-2 pl-10 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <p className="text-sm text-muted-foreground">
          {filtered.length} tenant{filtered.length !== 1 && "s"}
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {/* Empty state */}
      {!loading && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Building2 className="h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No tenants found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {search
              ? "Try a different search term."
              : "Create your first tenant to start white-labeling."}
          </p>
          {!search && (
            <button
              onClick={() => {
                setEditingTenant(null);
                setFormOpen(true);
              }}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Tenant
            </button>
          )}
        </div>
      )}

      {/* Tenant cards */}
      {!loading && filtered.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((tenant) => (
            <div
              key={tenant.id}
              className={`rounded-lg border bg-card text-card-foreground shadow-sm transition-all hover:shadow-md ${
                !tenant.active ? "opacity-60" : ""
              }`}
            >
              {/* Card header with branding color stripe */}
              <div
                className="h-2 rounded-t-lg"
                style={{ backgroundColor: getBrandColor(tenant) }}
              />

              <div className="p-5 space-y-4">
                {/* Tenant name and status */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {tenant.logo_url ? (
                      <img
                        src={tenant.logo_url}
                        alt={`${tenant.name} logo`}
                        className="h-10 w-10 rounded-lg object-contain border bg-background"
                      />
                    ) : (
                      <div
                        className="flex h-10 w-10 items-center justify-center rounded-lg"
                        style={{ backgroundColor: getBrandColor(tenant) + "20" }}
                      >
                        <Building2
                          className="h-5 w-5"
                          style={{ color: getBrandColor(tenant) }}
                        />
                      </div>
                    )}
                    <div>
                      <h3 className="font-semibold">{tenant.name}</h3>
                      <p className="text-xs text-muted-foreground">{tenant.domain}</p>
                    </div>
                  </div>
                  <span
                    className={`inline-flex h-2.5 w-2.5 rounded-full ${
                      tenant.active ? "bg-green-500" : "bg-red-400"
                    }`}
                    title={tenant.active ? "Active" : "Inactive"}
                  />
                </div>

                {/* License key */}
                <div className="rounded-md bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground mb-1">License Key</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 truncate text-xs font-mono bg-background rounded px-2 py-1 border">
                      {tenant.license_key}
                    </code>
                    <button
                      onClick={() => handleCopyKey(tenant.license_key)}
                      className="shrink-0 rounded-md border px-2 py-1 hover:bg-muted transition-colors"
                      title="Copy license key"
                    >
                      {copiedKey === tenant.license_key ? (
                        <Check className="h-3.5 w-3.5 text-green-600" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Telegram bot token */}
                {tenant.telegram_bot_token && (
                  <div className="text-xs text-muted-foreground">
                    <span className="font-medium">Bot:</span>{" "}
                    <code className="bg-muted rounded px-1.5 py-0.5">
                      {tenant.telegram_bot_token.substring(0, 20)}...
                    </code>
                  </div>
                )}

                {/* Actions row */}
                <div className="flex items-center gap-2 pt-2 border-t">
                  <button
                    onClick={() => {
                      setEditingTenant(tenant);
                      setFormOpen(true);
                    }}
                    className="flex-1 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleToggleActive(tenant)}
                    className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                      tenant.active
                        ? "border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950"
                        : "border-green-200 text-green-600 hover:bg-green-50 dark:border-green-800 dark:text-green-400 dark:hover:bg-green-950"
                    }`}
                    title={tenant.active ? "Deactivate tenant" : "Activate tenant"}
                  >
                    {tenant.active ? (
                      <>
                        <ToggleRight className="h-3.5 w-3.5" />
                        Deactivate
                      </>
                    ) : (
                      <>
                        <ToggleLeft className="h-3.5 w-3.5" />
                        Activate
                      </>
                    )}
                  </button>
                </div>

                {/* Footer meta */}
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    Created:{" "}
                    {tenant.created_at
                      ? new Date(tenant.created_at).toLocaleDateString()
                      : "N/A"}
                  </span>
                  {tenant.signature && (
                    <span className="truncate max-w-[120px]" title={tenant.signature}>
                      {tenant.signature.substring(0, 20)}...
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {formOpen && (
        <TenantFormModal
          tenant={editingTenant}
          onSaved={handleSaved}
          onClose={() => {
            setFormOpen(false);
            setEditingTenant(null);
          }}
        />
      )}
    </div>
  );
}