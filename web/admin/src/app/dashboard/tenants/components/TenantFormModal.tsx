"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { X, Upload, Loader2, RefreshCw } from "lucide-react";
import type { TenantData } from "../page";

interface TenantFormModalProps {
  tenant: TenantData | null;
  onSaved: () => void;
  onClose: () => void;
}

export function TenantFormModal({ tenant, onSaved, onClose }: TenantFormModalProps) {
  const isEdit = tenant !== null;

  const [name, setName] = useState(tenant?.name ?? "");
  const [domain, setDomain] = useState(tenant?.domain ?? "");
  const [telegramBotToken, setTelegramBotToken] = useState(tenant?.telegram_bot_token ?? "");
  const [signature, setSignature] = useState(tenant?.signature ?? "");
  const [active, setActive] = useState(tenant?.active ?? true);

  // Branding config
  const existingBranding = tenant?.branding_config as Record<string, string> | null;
  const [brandPrimaryColor, setBrandPrimaryColor] = useState(
    existingBranding?.primaryColor ?? existingBranding?.primary_color ?? "#3b82f6"
  );
  const [brandSecondaryColor, setBrandSecondaryColor] = useState(
    existingBranding?.secondaryColor ?? existingBranding?.secondary_color ?? "#6b7280"
  );
  const [brandFont, setBrandFont] = useState(
    existingBranding?.fontFamily ?? existingBranding?.font_family ?? "Inter, sans-serif"
  );
  const [showPrimaryPicker, setShowPrimaryPicker] = useState(false);
  const [showSecondaryPicker, setShowSecondaryPicker] = useState(false);

  // Logo
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(tenant?.logo_url ?? null);
  const [uploading, setUploading] = useState(false);

  // License
  const [licenseKey, setLicenseKey] = useState(tenant?.license_key ?? "");
  const [generatingKey, setGeneratingKey] = useState(false);

  // General state
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cleanup object URL on unmount
  useEffect(() => {
    return () => {
      if (logoPreview && logoPreview.startsWith("blob:")) {
        URL.revokeObjectURL(logoPreview);
      }
    };
  }, [logoPreview]);

  const generateLicenseKey = useCallback(async () => {
    try {
      setGeneratingKey(true);
      setError(null);
      const res = await api.post<{ license_key: string }>("/admin/tenants/generate-key");
      setLicenseKey(res.data.license_key);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate license key";
      setError(msg);
    } finally {
      setGeneratingKey(false);
    }
  }, []);

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogoFile(file);
    const previewUrl = URL.createObjectURL(file);
    // Revoke old preview if it was a blob
    if (logoPreview && logoPreview.startsWith("blob:")) {
      URL.revokeObjectURL(logoPreview);
    }
    setLogoPreview(previewUrl);
  };

  const uploadLogo = async (): Promise<string | null> => {
    if (!logoFile) return tenant?.logo_url ?? null;
    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", logoFile);
      const res = await api.post<{ url: string }>("/admin/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data.url;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload logo";
      setError(msg);
      return null;
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !domain.trim()) {
      setError("Name and domain are required.");
      return;
    }
    if (!licenseKey.trim() && !isEdit) {
      setError("License key is required. Generate one first.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      let logoUrl = tenant?.logo_url ?? null;
      if (logoFile) {
        logoUrl = await uploadLogo();
        if (!logoUrl) return; // upload failed, error already set
      }

      const payload: Record<string, unknown> = {
        name: name.trim(),
        domain: domain.trim(),
        telegram_bot_token: telegramBotToken.trim() || null,
        signature: signature.trim() || null,
        active,
        branding_config: {
          primaryColor: brandPrimaryColor,
          secondaryColor: brandSecondaryColor,
          fontFamily: brandFont,
        },
        logo_url: logoUrl,
      };

      if (!isEdit) {
        payload.license_key = licenseKey.trim();
      }

      if (isEdit) {
        await api.patch(`/admin/tenants/${tenant.id}`, payload);
      } else {
        await api.post("/admin/tenants", payload);
      }

      onSaved();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save tenant";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl border bg-card p-6 shadow-xl">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-muted transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <h2 className="text-xl font-bold mb-6">
          {isEdit ? "Edit Tenant" : "Create New Tenant"}
        </h2>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
            <p>{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <fieldset>
            <legend className="text-sm font-semibold text-foreground mb-3">
              Basic Information
            </legend>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. ACME Corp"
                  required
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Domain *</label>
                <input
                  type="text"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="e.g. acme.example.com"
                  required
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          </fieldset>

          {/* License Key */}
          {!isEdit && (
            <fieldset>
              <legend className="text-sm font-semibold text-foreground mb-3">
                License Key
              </legend>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={licenseKey}
                  onChange={(e) => setLicenseKey(e.target.value)}
                  placeholder="Generated license key..."
                  readOnly
                  className="flex-1 rounded-lg border bg-muted/50 px-3 py-2 text-sm font-mono outline-none focus:ring-2 focus:ring-primary"
                />
                <button
                  type="button"
                  onClick={generateLicenseKey}
                  disabled={generatingKey}
                  className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`h-4 w-4 ${generatingKey ? "animate-spin" : ""}`} />
                  Generate
                </button>
              </div>
            </fieldset>
          )}

          {/* Branding */}
          <fieldset>
            <legend className="text-sm font-semibold text-foreground mb-3">
              Branding & Appearance
            </legend>
            <div className="space-y-4">
              {/* Logo upload */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Logo</label>
                <div className="flex items-center gap-4">
                  {logoPreview ? (
                    <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-lg border bg-background">
                      <img
                        src={logoPreview}
                        alt="Logo preview"
                        className="h-full w-full object-contain"
                      />
                    </div>
                  ) : (
                    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg border bg-muted/50">
                      <Upload className="h-6 w-6 text-muted-foreground" />
                    </div>
                  )}
                  <label className="cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors">
                    {logoPreview ? "Change Logo" : "Upload Logo"}
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/svg+xml,image/webp"
                      onChange={handleLogoChange}
                      className="hidden"
                    />
                  </label>
                  {logoFile && (
                    <span className="text-xs text-muted-foreground">
                      {logoFile.name} ({(logoFile.size / 1024).toFixed(1)} KB)
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Supported: PNG, JPEG, SVG, WebP. Uploaded to MinIO storage.
                </p>
              </div>

              {/* Brand color: Primary */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Primary Color</label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowPrimaryPicker(!showPrimaryPicker);
                      setShowSecondaryPicker(false);
                    }}
                    className="h-8 w-8 rounded-md border shadow-sm"
                    style={{ backgroundColor: brandPrimaryColor }}
                  />
                  <input
                    type="text"
                    value={brandPrimaryColor}
                    onChange={(e) => setBrandPrimaryColor(e.target.value)}
                    className="w-28 rounded-lg border bg-background px-3 py-1.5 text-xs font-mono outline-none focus:ring-2 focus:ring-primary"
                  />
                  <span className="text-xs text-muted-foreground">
                    Used for headers, buttons, accents
                  </span>
                </div>
              {showPrimaryPicker && (
                  <div className="relative z-10 mt-2">
                    <div
                      className="fixed inset-0"
                      onClick={() => setShowPrimaryPicker(false)}
                    />
                    <div className="relative">
                      {/* Color presets grid */}
                      <div className="rounded-lg border bg-card p-3 shadow-lg">
                        <div className="grid grid-cols-7 gap-1.5 mb-3">
                          {[
                            "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
                            "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
                            "#06b6d4", "#d946ef", "#eab308", "#a855f7", "#10b981",
                            "#0ea5e9", "#f43f5e", "#7c3aed", "#249f24", "#d97706",
                            "#0891b2", "#be123c", "#4f46e5", "#65a30d", "#0e7490",
                            "#b91c1c", "#15803d", "#a16207", "#7e22ce", "#db2777",
                            "#0d9488", "#c2410c", "#4338ca", "#4d7c0f", "#0369a1",
                          ].map((color) => (
                            <button
                              key={color}
                              type="button"
                              onClick={() => setBrandPrimaryColor(color)}
                              className={`h-7 w-7 rounded-md border-2 transition-all hover:scale-110 ${
                                brandPrimaryColor === color
                                  ? "border-foreground scale-110"
                                  : "border-transparent"
                              }`}
                              style={{ backgroundColor: color }}
                              title={color}
                            />
                          ))}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">Custom:</span>
                          <input
                            type="color"
                            value={brandPrimaryColor}
                            onChange={(e) => setBrandPrimaryColor(e.target.value)}
                            className="h-7 w-10 cursor-pointer rounded border"
                          />
                          <span className="text-xs font-mono">{brandPrimaryColor}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Brand color: Secondary */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Secondary Color</label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowSecondaryPicker(!showSecondaryPicker);
                      setShowPrimaryPicker(false);
                    }}
                    className="h-8 w-8 rounded-md border shadow-sm"
                    style={{ backgroundColor: brandSecondaryColor }}
                  />
                  <input
                    type="text"
                    value={brandSecondaryColor}
                    onChange={(e) => setBrandSecondaryColor(e.target.value)}
                    className="w-28 rounded-lg border bg-background px-3 py-1.5 text-xs font-mono outline-none focus:ring-2 focus:ring-primary"
                  />
                  <span className="text-xs text-muted-foreground">
                    Used for backgrounds, borders, accents
                  </span>
                </div>
              {showSecondaryPicker && (
                  <div className="relative z-10 mt-2">
                    <div
                      className="fixed inset-0"
                      onClick={() => setShowSecondaryPicker(false)}
                    />
                    <div className="relative">
                      {/* Color presets grid */}
                      <div className="rounded-lg border bg-card p-3 shadow-lg">
                        <div className="grid grid-cols-7 gap-1.5 mb-3">
                          {[
                            "#6b7280", "#9ca3af", "#d1d5db", "#4b5563", "#374151",
                            "#78716c", "#a8a29e", "#d6d3d1", "#57534e", "#44403c",
                            "#71717a", "#a1a1aa", "#d4d4d8", "#52525b", "#3f3f46",
                            "#737373", "#a3a3a3", "#d4d4d4", "#525252", "#404040",
                            "#64748b", "#94a3b8", "#cbd5e1", "#475569", "#334155",
                            "#7c3aed", "#8b5cf6", "#a78bfa", "#6d28d9", "#5b21b6",
                            "#0891b2", "#22d3ee", "#67e8f9", "#06b6d4", "#0e7490",
                          ].map((color) => (
                            <button
                              key={color}
                              type="button"
                              onClick={() => setBrandSecondaryColor(color)}
                              className={`h-7 w-7 rounded-md border-2 transition-all hover:scale-110 ${
                                brandSecondaryColor === color
                                  ? "border-foreground scale-110"
                                  : "border-transparent"
                              }`}
                              style={{ backgroundColor: color }}
                              title={color}
                            />
                          ))}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">Custom:</span>
                          <input
                            type="color"
                            value={brandSecondaryColor}
                            onChange={(e) => setBrandSecondaryColor(e.target.value)}
                            className="h-7 w-10 cursor-pointer rounded border"
                          />
                          <span className="text-xs font-mono">{brandSecondaryColor}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Font family */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Font Family</label>
                <input
                  type="text"
                  value={brandFont}
                  onChange={(e) => setBrandFont(e.target.value)}
                  placeholder="Inter, sans-serif"
                  className="w-full max-w-xs rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          </fieldset>

          {/* Telegram & Signature */}
          <fieldset>
            <legend className="text-sm font-semibold text-foreground mb-3">
              Integration & Signature
            </legend>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Telegram Bot Token</label>
                <input
                  type="password"
                  value={telegramBotToken}
                  onChange={(e) => setTelegramBotToken(e.target.value)}
                  placeholder="e.g. 123456:ABC-DEF..."
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
                />
                <p className="text-xs text-muted-foreground">
                  Bot token for tenant-specific Telegram notifications.
                </p>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Email Signature / Legal Footer</label>
                <textarea
                  value={signature}
                  onChange={(e) => setSignature(e.target.value)}
                  placeholder="Optional email signature or legal footer text..."
                  rows={2}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary resize-none"
                />
              </div>
            </div>
          </fieldset>

          {/* Active toggle */}
          <div className="flex items-center gap-3">
            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                checked={active}
                onChange={(e) => setActive(e.target.checked)}
                className="peer sr-only"
              />
              <div className="h-6 w-11 rounded-full bg-muted after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:bg-green-500 peer-checked:after:translate-x-full" />
            </label>
            <span className="text-sm font-medium">
              {active ? "Active" : "Inactive"}
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 border-t pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || generatingKey || uploading}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {(saving || uploading) && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEdit ? "Save Changes" : "Create Tenant"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}