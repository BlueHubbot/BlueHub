"use client";

import { useState } from "react";
import { X, Plus, Trash2 } from "lucide-react";
import type { ProductData, ModuleOption } from "../page";

interface ProductFormModalProps {
  product: ProductData | null;
  modules: ModuleOption[];
  onSaved: () => void;
  onClose: () => void;
}

interface PriceTier {
  min_quantity: number;
  discount_percent: number;
}

interface PricingFormula {
  base_price: number;
  volume_discount: PriceTier[];
}

const defaultPricing: PricingFormula = {
  base_price: 9.99,
  volume_discount: [],
};

export function ProductFormModal({ product, modules, onSaved, onClose }: ProductFormModalProps) {
  const isEdit = !!product;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [moduleName, setModuleName] = useState(product?.module_name ?? "");
  const [productKey, setProductKey] = useState(product?.product_key ?? "");
  const [name, setName] = useState(product?.name ?? "");
  const [price, setPrice] = useState(product?.price ?? 9.99);
  const [billingCycle, setBillingCycle] = useState(product?.billing_cycle ?? "monthly");
  const [currency, setCurrency] = useState("USD");
  const [sortOrder, setSortOrder] = useState(product?.sort_order ?? 0);
  const [isActive, setIsActive] = useState(product?.is_active ?? true);

  // i18n descriptions
  const [descriptions, setDescriptions] = useState<Record<string, string>>(
    product?.description_i18n ?? { en: "", fa: "" }
  );

  // Metadata (previously "specs")
  const [metadataJson, setMetadataJson] = useState<string>(() => {
    if (product?.metadata) {
      return JSON.stringify(product.metadata, null, 2);
    }
    return JSON.stringify({ pricing_formula: defaultPricing }, null, 2);
  });
  const [metadataError, setMetadataError] = useState<string | null>(null);

  const addLang = () => {
    const existing = Object.keys(descriptions).sort();
    const candidates = ["en", "fa", "ar", "tr", "ru", "de", "fr", "es", "zh", "pt"];
    const next = candidates.find((c) => !existing.includes(c));
    if (next) {
      setDescriptions((prev) => ({ ...prev, [next]: "" }));
    }
  };

  const removeLang = (lang: string) => {
    setDescriptions((prev) => {
      const next = { ...prev };
      delete next[lang];
      return next;
    });
  };

  const validateMetadata = (json: string): boolean => {
    try {
      JSON.parse(json);
      setMetadataError(null);
      return true;
    } catch {
      setMetadataError("Invalid JSON syntax");
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!moduleName || !productKey || !name) {
      setError("Module, Product Key, and Name are required.");
      return;
    }
    if (!validateMetadata(metadataJson)) return;

    const metadata = JSON.parse(metadataJson);
    const payload = {
      module_name: moduleName,
      product_key: productKey,
      name,
      description_i18n: Object.fromEntries(
        Object.entries(descriptions).filter(([, v]) => v.trim())
      ),
      price,
      billing_cycle: billingCycle,
      currency,
      is_active: isActive,
      metadata,
      sort_order: sortOrder,
    };

    try {
      setSaving(true);
      if (isEdit && product) {
        await apiPatch(`/admin/products/${product.id}`, payload);
      } else {
        await apiPost("/admin/products", payload);
      }
      onSaved();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save product";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-xl border bg-background shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-lg font-semibold">
            {isEdit ? `Edit Product: ${product?.name}` : "Create New Product"}
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
              {error}
            </div>
          )}

          {/* Row: Module + Key */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">Module *</label>
              <select
                value={moduleName}
                onChange={(e) => setModuleName(e.target.value)}
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
                required
              >
                <option value="">Select module...</option>
                {modules.map((m) => (
                  <option key={m.module_name} value={m.module_name}>
                    {m.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Product Key *</label>
              <input
                type="text"
                value={productKey}
                onChange={(e) => setProductKey(e.target.value)}
                placeholder="e.g. vpn-premium-monthly"
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
                required
              />
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="mb-1.5 block text-sm font-medium">Display Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. VPN Premium (Monthly)"
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>

          {/* Row: Price + Currency + Billing */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1.5 block text-sm font-medium">Price ($)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={price}
                onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Currency</label>
              <input
                type="text"
                maxLength={3}
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                placeholder="USD"
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Billing Cycle</label>
              <select
                value={billingCycle}
                onChange={(e) => setBillingCycle(e.target.value)}
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="semi_annual">Semi-Annual</option>
                <option value="annual">Annual</option>
                <option value="lifetime">Lifetime</option>
              </select>
            </div>
          </div>

          {/* Row: Sort Order + Active */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">Sort Order</label>
              <input
                type="number"
                min="0"
                value={sortOrder}
                onChange={(e) => setSortOrder(parseInt(e.target.value) || 0)}
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <span className="text-sm font-medium">Product Active</span>
              </label>
            </div>
          </div>

          {/* i18n Descriptions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">Multi-Language Descriptions</label>
              <button
                type="button"
                onClick={addLang}
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                <Plus className="h-3 w-3" />
                Add language
              </button>
            </div>
            <div className="space-y-2">
              {Object.entries(descriptions).map(([lang, text]) => (
                <div key={lang} className="flex items-start gap-2">
                  <span className="mt-2.5 rounded bg-muted px-2 py-0.5 text-xs font-medium uppercase">
                    {lang}
                  </span>
                  <textarea
                    value={text}
                    onChange={(e) =>
                      setDescriptions((prev) => ({ ...prev, [lang]: e.target.value }))
                    }
                    rows={2}
                    placeholder={`Description in ${lang}...`}
                    className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button
                    type="button"
                    onClick={() => removeLang(lang)}
                    className="mt-2 rounded p-1 text-muted-foreground hover:text-red-500 transition-colors"
                    title={`Remove ${lang}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Metadata (JSON editor) */}
          <div>
            <label className="mb-1.5 block text-sm font-medium">
              Metadata (JSON)
            </label>
            <p className="mb-1.5 text-xs text-muted-foreground">
              Pricing formula, traffic, speed, RAM, disk, and other product specs.
            </p>
            <textarea
              value={metadataJson}
              onChange={(e) => {
                setMetadataJson(e.target.value);
                if (metadataError) validateMetadata(e.target.value);
              }}
              onBlur={() => validateMetadata(metadataJson)}
              rows={8}
              className="w-full rounded-lg border bg-muted/30 px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-primary"
            />
            {metadataError && (
              <p className="mt-1 text-xs text-red-500">{metadataError}</p>
            )}
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !!metadataError}
            onClick={handleSubmit}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : isEdit ? "Update Product" : "Create Product"}
          </button>
        </div>
      </div>
    </div>
  );
}

// Temporary inline API helpers (same pattern as lib/api.ts)
async function apiPost(url: string, body: unknown) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}${url}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiPatch(url: string, body: unknown) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}${url}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}